import os
from string import Template

def init(_template_dir, _out_prefix):
        global template_dir
        global out_prefix
        template_dir = _template_dir
        out_prefix = _out_prefix

def emit_printf(connection, printfs):
        global template_dir
        global out_prefix
        with open(os.path.join(template_dir, "printf.template.c"), 'r') as f:
                template = Template(f.read())

        #Give each printf an "index" if they don't already have it
        for index in range(len(printfs)):
                printf = printfs[index]
                if printf["header_bitwidth"] != 8:
                        raise ValueError
                if "index" in printf and printf["index"] != index:
                        raise ValueError
                printf["index"] = index;

        fargs = {}

        def make_compute_arg(printf, i):
                compute_arg_template = Template(\
r"""
$dtype $name = pull_bits_$dtype(&iter,$nbits);
""")
                nbits = printf["arg_bitwidths"][i]
                return compute_arg_template.safe_substitute(
                        printf,
                        dtype="long" if nbits > 32 else "int",
                        name="x%d"%i,
                        nbits=nbits,
                )

        def make_case(printf):
                nargs = len(printf["arg_bitwidths"])
                compute_args = "\n".join(
                        make_compute_arg(printf,i) for i in range(nargs)
                )
                args = ", ".join("x%d"%i for i in range(nargs))
                case_template = Template(\
r"""
case $index:
{
        $compute_args
        printf("$msg" "\n" $args);
}
break;
""")
                return case_template.safe_substitute(
                        printf,
                        compute_args = compute_args,
                        args = ", " + args if len(args) else ""
                )

        fargs["PRINTF_CASES"] = "\n".join(
                make_case(printf) for printf in printfs
        )
        HEADER_SIZE = 1
        fargs["PRINTF_ARGLENGTHS"] = ", ".join(
                str(printf["total_byte_len"]-HEADER_SIZE) for printf in printfs
        )

        #fargs[] = ""
        print(fargs)

        generated = template.safe_substitute(fargs)
        #print(generated)

        with open(out_prefix+"-io.c", 'w') as f:
                f.write(generated)
