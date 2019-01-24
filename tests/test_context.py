"""Module to test Context functionality"""

import threading
import time

from protean.context import context
from protean.core import field
from protean.core.entity import Entity
from protean.core.repository import repo_factory
from protean.core.tasklet import Tasklet
from protean.core.usecase import CreateRequestObject
from protean.core.usecase import CreateUseCase
from protean.impl.repository.dict_repo import DictModel


class CreateUseCase2(CreateUseCase):

    """ Updated Create use case to handle context """
    def process_request(self, request_object):
        """Process Create Resource Request"""
        request_object.data['created_by'] = getattr(
            context, 'account', 'anonymous')
        return super().process_request(request_object)


class ThreadedDog(Entity):
    """This is a dummy Dog Entity class"""
    name = field.String(required=True, max_length=50)
    created_by = field.String(required=True, max_length=15)


class ThreadedDogModel(DictModel):
    """ Model for the ThreadedDog Entity"""

    class Meta:
        """ Meta class for schema options"""
        entity = ThreadedDog
        model_name = 'threaded_dogs'


repo_factory.register(ThreadedDogModel)


def run_create_task(thread_name, name, sleep=0):
    """Assert on Request URL"""
    if thread_name:
        context.set_context({'account': thread_name})
    # Sleep for some determinate time to allow other threads to
    # move forward
    time.sleep(sleep)

    Tasklet.perform(ThreadedDog, CreateUseCase2, CreateRequestObject, {'name': name})


def test_context_with_threads():
    """ Test context information is passed to use cases"""

    # Run 5 threads and create multiple objects
    threads = [
        threading.Thread(target=run_create_task,
                         args=(None, 'Johnny', 0.6)),
        threading.Thread(target=run_create_task,
                         args=('thread_2', 'Carey')),
        threading.Thread(target=run_create_task,
                         args=('thread_3', 'Mustache', 0.3)),
        threading.Thread(target=run_create_task,
                         args=('thread_4', 'Rocky')),
        threading.Thread(target=run_create_task,
                         args=('thread_5', 'Prince', 0.4))
    ]

    for t in threads:
        t.start()

    # Wait for all threads to complete
    for t in threads:
        t.join()

    # Get the list of dogs and validate the results
    dogs = ThreadedDog.query(per_page=10)
    assert dogs.total == 5
    for dog in dogs.items:
        if dog.name == 'Johnny':
            assert dog.created_by == 'anonymous'
        if dog.name == 'Carey':
            assert dog.created_by == 'thread_2'
        if dog.name == 'Mustache':
            assert dog.created_by == 'thread_3'
        if dog.name == 'Rocky':
            assert dog.created_by == 'thread_4'
        if dog.name == 'Price':
            assert dog.created_by == 'thread_5'

    # Cleanup the database
    repo_factory.ThreadedDog.delete_all()
