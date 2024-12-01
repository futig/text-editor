from common.operations import *


def _insert_insert(insert1: InsertOperation, insert2: InsertOperation) -> InsertOperation:
    if insert1.index < insert2.index:
        return insert2
    return InsertOperation(insert2.index + len(insert1.text_to_insert), insert2.text_to_insert)


def _insert_delete(insert: InsertOperation, delete: DeleteOperation) -> DeleteOperation:
    if insert.index >= delete.begin:
        return delete
    return DeleteOperation(delete.begin + len(insert.text_to_insert), delete.end + len(insert.text_to_insert))


def _delete_insert(delete: DeleteOperation, insert: InsertOperation) -> InsertOperation:
    if delete.begin <= insert.index:
        return InsertOperation(insert.index - (delete.end - delete.begin), insert.text_to_insert)
    return insert


def _delete_delete(delete: DeleteOperation, prev_delete: DeleteOperation) -> DeleteOperation:
    if delete.begin < prev_delete.begin:
        return delete
    elif delete.begin > prev_delete.begin:
        return DeleteOperation(delete.begin - prev_delete.length, delete.end - prev_delete.length)
    return None


def convert_operation(operation, previous_operation):
    if not previous_operation or type(previous_operation) is CreateServerOperation:
        return operation
    if type(previous_operation) is InsertOperation:
        if type(operation) is InsertOperation:
            operation_to_perform = _insert_insert(previous_operation,
                                                  operation)
        elif type(operation) is DeleteOperation:
            operation_to_perform = _insert_delete(previous_operation,
                                                  operation)
    elif type(previous_operation) is DeleteOperation:
        if type(operation) is InsertOperation:
            operation_to_perform = _delete_insert(previous_operation,
                                                  operation)
        elif type(operation) is DeleteOperation:
            operation_to_perform = _delete_delete(previous_operation,
                                                  operation)
    return operation_to_perform
