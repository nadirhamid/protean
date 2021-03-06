# Standard Library Imports
from datetime import datetime

# Protean
import pytest

from protean.core.aggregate import BaseAggregate
from protean.core.exceptions import ValidationError
from protean.core.field.basic import (
    Auto,
    Boolean,
    Date,
    DateTime,
    Float,
    Identifier,
    Integer,
    List,
    String,
)
from sqlalchemy import types as sa_types


class ArrayUser(BaseAggregate):
    email = String(max_length=255, required=True, unique=True)
    roles = List()  # Defaulted to String Content Type


class IntegerArrayUser(BaseAggregate):
    email = String(max_length=255, required=True, unique=True)
    roles = List(content_type=Integer)


@pytest.mark.sqlite
def test_array_data_type_association(test_domain):
    test_domain.register(ArrayUser)

    model_cls = test_domain.get_model(ArrayUser)
    type(model_cls.roles.property.columns[0].type) == sa_types.ARRAY


@pytest.mark.sqlite
def test_basic_array_data_type_operations(test_domain):
    test_domain.register(ArrayUser)

    model_cls = test_domain.get_model(ArrayUser)

    user = ArrayUser(email="john.doe@gmail.com", roles=["ADMIN", "USER"])
    user_model_obj = model_cls.from_entity(user)

    user_copy = model_cls.to_entity(user_model_obj)
    assert user_copy is not None
    assert user_copy.roles == ["ADMIN", "USER"]


@pytest.mark.sqlite
def test_array_content_type_validation(test_domain):
    test_domain.register(ArrayUser)
    test_domain.register(IntegerArrayUser)

    for kwargs in [
        {"email": "john.doe@gmail.com", "roles": [1, 2]},
        {"email": "john.doe@gmail.com", "roles": ["1", 2]},
        {"email": "john.doe@gmail.com", "roles": [1.0, 2.0]},
        {"email": "john.doe@gmail.com", "roles": [datetime.utcnow()]},
    ]:
        with pytest.raises(ValidationError) as exception:
            ArrayUser(**kwargs)
        assert exception.value.messages == {"roles": ["Invalid value"]}

    model_cls = test_domain.get_model(IntegerArrayUser)
    user = IntegerArrayUser(email="john.doe@gmail.com", roles=[1, 2])
    user_model_obj = model_cls.from_entity(user)

    user_copy = model_cls.to_entity(user_model_obj)
    assert user_copy is not None
    assert user_copy.roles == [1, 2]

    for kwargs in [
        {"email": "john.doe@gmail.com", "roles": ["ADMIN", "USER"]},
        {"email": "john.doe@gmail.com", "roles": ["1", "2"]},
        {"email": "john.doe@gmail.com", "roles": [datetime.utcnow()]},
    ]:
        with pytest.raises(ValidationError) as exception:
            IntegerArrayUser(**kwargs)
        assert exception.value.messages == {"roles": ["Invalid value"]}


@pytest.mark.sqlite
def test_that_only_specific_primitive_types_are_allowed_as_content_types(test_domain):
    List(content_type=String)
    List(content_type=Identifier)
    List(content_type=Integer)
    List(content_type=Float)
    List(content_type=Boolean)
    List(content_type=Date)
    List(content_type=DateTime)

    with pytest.raises(ValidationError) as error:
        List(content_type=Auto)

    assert error.value.messages == {"content_type": ["Content type not supported"]}
