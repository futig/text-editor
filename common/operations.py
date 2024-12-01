from abc import ABCMeta, abstractmethod


class Operation:
    __metaclass__ = ABCMeta

    @abstractmethod
    def do(self, text):
        pass

    @abstractmethod
    def redo(self):
        pass

    @abstractmethod
    def to_dict(self):
        pass


class InsertOperation(Operation):
    def __init__(self, index: int, text: str):
        self.name = 'Insert'
        self.text_to_insert = text
        self.index = index

    def do(self, text):
        return f"{text[:self.index]}{self.text_to_insert}{text[self.index:]}"

    def redo(self):
        raise NotImplementedError

    def to_dict(self):
        return {
            'name': 'Insert',
            'text': self.text_to_insert,
            'index': self.index
        }


class DeleteOperation(Operation):

    def __init__(self, begin, end):
        self.begin = begin
        self.end = end
        self.name = 'Delete'
        self.length = end - begin

    def do(self, text):
        temp = f"{text[:self.begin]}{text[self.end:]}"
        return temp

    def redo(self):
        raise NotImplementedError

    def to_dict(self):
        return {
            'name': self.name,
            'begin': self.begin,
            'end': self.end
        }


class CreateServerOperation(Operation):

    def to_dict(self):
        return {
            'name': self.name,
            'file': self.file,
        }

    def __init__(self, file):
        self.file = file
        self.name = 'Create'

    def do(self, text=None):
        pass

    def redo(self):
        raise NotImplementedError


class ConnectServerOperation(Operation):

    def __init__(self, file_id):
        self.name = "Connect"
        self.file_id = file_id

    def redo(self):
        raise NotImplementedError

    def to_dict(self):
        return {
            'name': self.name,
            'file_id': self.file_id,
        }

    def do(self, text):
        raise NotImplementedError


# class StyleOperation(Operation):
#     def redo(self):
#         pass
#
#     def do(self):
#         pass


def operation_from_json(dict):
    if dict['name'] == 'Insert':
        return InsertOperation(dict['index'], dict['text'])
    if dict['name'] == 'Delete':
        return DeleteOperation(dict['begin'], dict['end'])
    if dict['name'] == 'Create':
        return CreateServerOperation(dict['file'])
    if dict['name'] == 'Connect':
        return ConnectServerOperation(dict['file_id'])
    return None
