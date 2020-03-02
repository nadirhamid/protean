import re

from collections import defaultdict
from datetime import datetime

from elasticsearch_dsl import Text, Keyword

from protean.core.aggregate import BaseAggregate
from protean.core.field.basic import DateTime, Integer, String
from protean.core.field.basic import Text as ProteanText
from protean.core.field.embedded import ValueObjectField
from protean.core.value_object import BaseValueObject
from protean.impl.repository.elasticsearch_repo import ElasticsearchModel


class Person(BaseAggregate):
    first_name = String(max_length=50, required=True)
    last_name = String(max_length=50, required=True)
    age = Integer(default=21)
    created_at = DateTime(default=datetime.now())


class Email(BaseValueObject):
    REGEXP = r'\"?([-a-zA-Z0-9.`?{}]+@\w+\.\w+)\"?'

    # This is the external facing data attribute
    address = String(max_length=254, required=True)

    def clean(self):
        """ Business rules of Email address """
        errors = defaultdict(list)

        if not bool(re.match(Email.REGEXP, self.address)):
            errors['address'].append("is invalid")

        return errors


class ComplexUser(BaseAggregate):
    email = ValueObjectField(Email, required=True)
    password = String(required=True, max_length=255)


class Provider(BaseAggregate):
    name = ProteanText()
    about = ProteanText()


class ProviderCustomModel(ElasticsearchModel):
    name = Text(fields={'raw': Keyword()})
    about = Text()

    class Meta:
        entity_cls = Provider