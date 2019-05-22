import pytest

from collections import OrderedDict
from datetime import datetime

from protean.core.aggregate import _AggregateMetaclass
from protean.core.exceptions import ValidationError
from protean.utils import fully_qualified_name

from .elements import Role, SubclassRole, Person, ConcreteRole


class TestAggregateStructure:
    def test_aggregate_inheritance(self):
        assert isinstance(Role, _AggregateMetaclass)

    def test_successful_aggregate_registration(self, test_domain):
        test_domain.register(Role)
        assert fully_qualified_name(Role) in test_domain.aggregates

    def test_aggregate_field_definitions(self):
        declared_fields_keys = list(OrderedDict(sorted(Role.meta_.declared_fields.items())).keys())
        assert declared_fields_keys == ['created_on', 'id', 'name']


class TestSubclassedAggregateStructure:
    def test_subclass_aggregate_field_definitions(self):
        declared_fields_keys = list(OrderedDict(sorted(SubclassRole.meta_.declared_fields.items())).keys())
        assert declared_fields_keys == ['created_on', 'id', 'name']

    def test_that_fields_in_base_classes_are_inherited(self):
        declared_fields_keys = list(OrderedDict(sorted(ConcreteRole.meta_.declared_fields.items())).keys())
        assert declared_fields_keys == ['bar', 'foo', 'id']

        role = ConcreteRole(id=3, foo='foo', bar='bar')
        assert role is not None
        assert role.foo == 'foo'


class TestAggregateInitialization:
    def test_successful_aggregate_initialization(self):
        role = Role(name='ADMIN')
        assert role is not None
        assert role.name == 'ADMIN'
        assert type(role.created_on) is datetime

    def test_individuality(self):
        """Test successful Account Entity initialization"""

        role1 = Role(name='ADMIN')
        role2 = Role(name='USER')
        assert role1.name == 'ADMIN'
        assert role2.name == 'USER'

    def test_initialization_from_dict_template(self):
        with pytest.raises(AssertionError):
            Person('John Doe')

        person = Person({'first_name': 'John', 'last_name': 'Doe', 'age': 23})
        assert person.first_name == 'John'
        assert person.last_name == 'Doe'
        assert person.age == 23

    def test_error_message_content_on_validation_error(self):
        # Single error message
        try:
            Person(last_name='Doe')
        except ValidationError as err:
            assert err.messages == {
                'first_name': ['is required']}

        # Test multiple error messages
        try:
            Person(last_name='Doe', age='old')
        except ValidationError as err:
            assert err.messages == {
                'first_name': ['is required'],
                'age': ['"old" value must be an integer.']
                }


class TestAggregateFieldValues:
    def test_that_validation_error_is_raised_if_required_fields_are_not_provided(self):
        with pytest.raises(ValidationError):
            Role(id=123423)

    def test_that_field_values_are_defaulted_when_not_provided(self):
        """Test that values are defaulted properly"""
        person = Person(first_name='John', last_name='Doe')
        assert person.age == 21

    def test_that_field_values_with_default_settings_can_be_specified_explicitly(self):
        """Test that values are defaulted properly"""
        person = Person(first_name='John', last_name='Doe', age=35)
        assert person.age == 35

    def test_that_validation_error_is_raised_when_specified_string_length_is_breached(self):
        """Test validation of String length checks"""
        with pytest.raises(ValidationError):
            Role(name='ABCDEFGHIJKLMNOPQR')

    def test_that_values_are_validated_against_specified_data_types(self):
        """Test validation of data types of values"""
        with pytest.raises(ValidationError):
            Person(first_name='John', age="Young")
