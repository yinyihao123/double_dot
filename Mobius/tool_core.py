class Tool:


    def __init__(
        self,
        name,
        description,
        func,
        parameters,
        required=None
    ):

        self.name = name
        self.description = description
        self.func = func
        self.parameters = parameters
        self.required = required or []


    def schema(self):

        return {

            "name":self.name,

            "description":self.description,

            "parameters": self.parameters,
            "required": list(self.required)

        }
