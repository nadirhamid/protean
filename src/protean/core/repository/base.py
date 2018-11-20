""" Define the interfaces for Repository implementations """
import logging

from abc import ABCMeta
from abc import abstractmethod

import collections

from typing import Any

from protean.core.entity import Entity
from protean.core.field import Field
from protean.core.exceptions import ValidationError, ConfigurationError, \
    ObjectNotFoundError
from protean.utils.meta import OptionsMeta
from protean.utils import inflection

from .pagination import Pagination

logger = logging.getLogger('protean.repository')


class BaseRepository(metaclass=ABCMeta):
    """Repository interface to interact with databases

    :param conn: A connection/session to the data source of the schema
    :param schema_cls: The schema class registered with this repository
    """

    def __init__(self, conn, schema_cls):
        self.conn = conn
        self.schema = schema_cls()
        self.schema_name = schema_cls.__name__

    @abstractmethod
    def _filter_objects(self, page: int = 1, per_page: int = 10,
                        order_by: list = (), _excludes: dict = None,
                        **filters) -> Pagination:
        """
        Filter objects from the repository. Method must return a `Pagination`
        object
        """

    def get(self, identifier: Any) -> Entity:
        """Get a specific Record from the Repository

        :param identifier: id of the record to be fetched from the repository.

        """
        logger.debug(
            f'Lookup {self.schema_name} object with identifier {identifier}')
        # Get the ID field for the entity
        entity_cls = self.schema.opts.entity_cls
        filters = {
            entity_cls.meta_.id_field[0]: identifier
        }

        # Find this item in the repository or raise Error
        results = self._filter_objects(**filters)
        if not results.items:
            raise ObjectNotFoundError(
                f'{self.schema_name} object with identifier {identifier} '
                f'does not exist.')

        # Convert to entity and return it
        return self.schema.to_entity(results.first)

    def filter(self, page: int = 1, per_page: int = 10, order_by: list = (),
               _excludes: dict = None, **filters) -> Pagination:
        """
        Read Record(s) from the repository. Method must return a `Pagination`
        object

        :param page: The current page number of the records to be pulled
        :param per_page: The size of each page of the records to be pulled
        :param order_by: The list of parameters to be used for ordering the
        results. Use a `-` before the parameter name to sort in descending
        order and if not ascending order.
        :param _excludes: Objects with these properties will be excluded
        from the results

        :return Returns a `Pagination` object that holds the filtered results
        """
        logger.debug(
            f'Query {self.schema_name} objects with filters {filters} and '
            f'order results by {order_by}')

        # order_by clause must be list of keys
        order_by = self.schema.opts.order_by if not order_by else order_by
        if not isinstance(order_by, collections.Iterable):
            order_by = [order_by]

        # Call the read method of the repository
        results = self._filter_objects(page, per_page, order_by, _excludes,
                                       **filters)

        # Convert the returned results to entity and return it
        entity_items = []
        for item in results.items:
            entity_items.append(self.schema.to_entity(item))
        results.items = entity_items

        return results

    def exists(self, _excludes, **filters):
        """ Return `True` if objects matching the provided filters and excludes
        exist if not return false.

        Call the filter query by default. Can be overridden for better and
        quicker implementations.

        :param _excludes: entities without this combination of field name and
        values will be returned
        """
        results = self._filter_objects(_excludes=_excludes, **filters)
        return bool(results)

    @abstractmethod
    def _create_object(self, entity: Entity) -> Entity:
        """Create a new schema object from the entity"""

    def create(self, *args, **kwargs) -> Entity:
        """Create a new record in the repository"""
        logger.debug(
            f'Creating new {self.schema_name} object using data {kwargs}')

        # Build the entity from the input arguments
        entity = self.schema.opts.entity_cls(*args, **kwargs)

        # Do unique checks, create this object and return it
        self.validate_unique(entity)
        entity = self._create_object(entity)
        return entity

    @abstractmethod
    def _update_object(self, entity: Entity) -> Entity:
        """Update a schema object in the repository and return it"""

    def update(self, identifier: Any, data: dict) -> Entity:
        """Update a Record in the repository

        :param identifier: The id of the record to be updated
        :param data: A dictionary of record properties to be updated
        """
        logger.debug(
            f'Updating existing {self.schema_name} object with id {identifier} '
            f'using data {data}')

        # Get the entity and update it
        entity = self.get(identifier)
        entity.update(data)

        # Do unique checks, update the record and return the Entity
        self.validate_unique(entity, create=False)
        entity = self._update_object(entity)
        return entity

    def validate_unique(self, entity, create=True):
        """ Validate the unique constraints for the entity """
        # Build the filters from the unique constraints
        filters, excludes = {}, {}
        for field_name, field_obj in entity.meta_.unique_fields:
            lookup_value = getattr(entity, field_name, None)
            # Ignore empty lookup values
            if lookup_value in Field.empty_values:
                continue
            # Ignore identifiers on updates
            if not create and field_obj.identifier:
                excludes[field_name] = lookup_value
                continue
            filters[field_name] = lookup_value

        # Lookup the objects by the filters and raise error on results
        for filter_key, lookup_value in filters.items():
            if self.exists(excludes, **{filter_key: lookup_value}):
                field_obj = entity.meta_.declared_fields[filter_key]
                field_obj.fail('unique',
                               schema_name=self.schema.opts.schema_name,
                               field_name=filter_key)

    @abstractmethod
    def delete(self, identifier: Any):
        """Delete a Record from the Repository"""


class RepositorySchemaOpts(object):
    """class Meta options for the :class:`RepositorySchema`."""

    def __init__(self, meta, schema_cls):
        self.entity_cls = getattr(meta, 'entity', None)
        if not self.entity_cls or not issubclass(self.entity_cls, Entity):
            raise ConfigurationError(
                '`entity` option must be set and be a subclass of `Entity`.')

        # Get the schema name to be used, if not provided default it
        self.schema_name = getattr(meta, 'schema_name', None)
        if not self.schema_name:
            self.schema_name = inflection.underscore(schema_cls.__name__)

        # Get the database bound to this schema
        self.bind = getattr(meta, 'bind', 'default')

        # Default ordering of the filter response
        self.order_by = getattr(meta, 'order_by', ())


class BaseRepositorySchema(metaclass=OptionsMeta):
    """ Repository Schema defines an index/table in the repository"""
    options_class = RepositorySchemaOpts
    opts = None

    class Meta(object):
        """Options object for a Schema.
        Example usage: ::
            class Meta:
                entity = Dog
        Available options:
        - ``base``: Indicates that this is a base schema so ignore the meta
        - ``entity``: the entity associated with this schema.
        - ``schema_name``: name of this schema that will be used as table/index
        names, defaults to underscore version of the class name.
        - ``bind``: the name of the repository connection associated with this
        schema, default value is `default`.
        - ``order_by``: default ordering of objects returned by filter queries.
        """
        base = True

    @property
    def name(self):
        """ Return the name of the schema"""
        return self.opts.schema_name

    @abstractmethod
    def from_entity(self, entity):
        """Initialize Repository Schema object from Entity object"""

    @abstractmethod
    def to_entity(self, *args, **kwargs):
        """Convert Repository Schema Object to Entity Object"""


class BaseConnectionHandler(metaclass=ABCMeta):
    """ Interface to manage connections to the database """
    @abstractmethod
    def get_connection(self):
        """ Get the connection object for the repository"""
