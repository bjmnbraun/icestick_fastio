def init(_template_dir):
        global template_dir
        template_dir = _template_dir

def emit():
        global template_dir
        print(template_dir)
