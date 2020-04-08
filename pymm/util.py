def dict_to_list(d:dict):
    res = []
    for (key, item) in d.items():
        is_dict = False
        if isinstance(item, dict):
            item = dict_to_list(item)
            is_dict = True
        res.append((key, is_dict, item))
    return res

def tuple_to_dict(t:tuple):
    res = {}
    for (key, is_dict, item) in t:
        if is_dict:
            item = tuple_to_dict(item)
        res[key] = item
    return res


error_dict = {
    'get': (AttributeError, NameError),
    'index': LookupError,
    'reference': ('get', 'index'),
    'value': (TypeError, ValueError),
    'directory': (IsADirectoryError, NotADirectoryError),
    'file': (FileExistsError, FileNotFoundError, PermissionError, 'directory'),
    'os': OSError,
}

res, subname, suberror = (None,) * 3
new_error_dict = {}
for (name, error) in error_dict.items():
    if isinstance(name, tuple):
        for subname in name:
            new_error_dict[subname] = error
    else:
        new_error_dict[name] = error
error_dict = new_error_dict
new_error_dict = {}
for (name, error) in error_dict.items():
    if isinstance(error, str):
        new_error_dict[name] = new_error_dict[error]
    elif isinstance(error, tuple):
        res = []
        for suberror in error:
            if isinstance(suberror, str):
                res.extend(new_error_dict[suberror])
            else:
                res.append(suberror)
        new_error_dict[name] = tuple(res)
    else:
        new_error_dict[name] = (error,)
error_dict = new_error_dict
del res, subname, suberror, new_error_dict, name, error

def error_from_id(id):
    if id in error_dict:
        return error_dict[id][0]
    return Exception
def id_from_error(error):
    for (key, item) in error_dict.items():
        if error in item:
            return key
def error_info(error):
    return id_from_error(error.__class__), error.args, {
        x: getattr(error, x) for x in dir(error)
        if x[0] != '_'
        if x != 'args' and x != 'with_traceback'
        if hasattr(error, x)
    }
def error_from_info(info):
    id, args, data = info
    error = error_from_id(id)(*args)
    for (name, value) in data.items():
        setattr(error, name, value)
    return error