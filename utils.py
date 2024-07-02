
def inspect_object(obj: object):
    """Inspect methods and variables of an object."""

    def list_class_attributes(obj):
        methods = []
        variables = []

        for attribute_name in dir(obj):
            attribute = getattr(obj, attribute_name)
            if callable(attribute):
                methods.append(attribute_name)
            else:
                variables.append(attribute_name)
        
        return methods, variables

    methods, variables = list_class_attributes(obj.__class__)

    print("Methods:")
    for method in methods:
        print(method)

    print("\nVariables:")
    for variable in variables:
        print(variable)