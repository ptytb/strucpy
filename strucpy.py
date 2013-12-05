#!/usr/bin/python2.7

from pycparser import parse_file, c_ast
from pycparser import c_parser
from pycparser.c_ast import *

ast = None
labelOrd = 0
hook = {}
def loadtypedefs():
    global ast
    ast = parse_file("example.c")

def gettype(NAME):
        class TypedeclVisitor(NodeVisitor):
                def __init__(self):
                    self.found = []

                def visit_Typedef(self, node):
                    if node.name == NAME:
                        self.found.append(node)

        td = TypedeclVisitor()
        td.visit(ast)
        return td.found[0] if td.found else None

def write_c(s):
    print s

def askIsArray(FIELD):
    msg = "Is field \"{0}\" an array?".format(FIELD)
    return True if raw_input("%s (y/N) " % msg).lower() == 'y' else False

def askArrayLengthField():
    print "Enter field determing array length: "
    return raw_input()

def isStdType(NAME):
    return NAME in ("int", "float", "void", "char", "signed",
                    "unsigned", "auto", "short", "long")

def isPodType(TYPE):
#    print "checking {0}\n".format(TYPE)
    if hasattr(TYPE, "POD"):
        return TYPE.POD

    t = type(TYPE)
    result = False

    if t in (Typedef, TypeDecl, Decl, ArrayDecl):
#        if t is Typedef:
#            print "checking type {0}\n".format(TYPE.name)
        result = all(map(isPodType, (TYPE.type,)))
    elif t in (Struct, Union):
        result = all(map(isPodType, fields(TYPE)))
    elif t is IdentifierType:
        result = all(map(
            lambda n : True if isStdType(n) else isPodType(gettype(n))
                , TYPE.names));
    elif t is (Constant,):
        result = True

    TYPE.POD = result
    return result;

def isPointer(TYPE):
    return type(TYPE) is PtrDecl \
                or hasattr(TYPE, "type") \
                and type(TYPE.type) is PtrDecl;

def deref(TYPE):
    if type(TYPE) is PtrDecl:
        return TYPE.type
    elif hasattr(TYPE, "type") and type(TYPE.type) is PtrDecl:
        return TYPE.type.type
    return None

def fields(TYPE):
    return TYPE.decls if type(TYPE) in [ Struct, Union ] else []

def hooked(ATYPE, BTYPE):
    pass

def hook(A, ATYPE, B, BTYPE):
    pass

def struct_copy_rec(A, ATYPE, B, BTYPE):
    if hooked(ATYPE, BTYPE):
        write_c(hook(A, ATYPE, B, BTYPE))
        return

    while type(ATYPE) in (Typedef, TypeDecl):
            ATYPE = ATYPE.type

    if type(ATYPE) is IdentifierType:
        E = gettype(ATYPE.names[0])
        ATYPE = E if E else ATYPE;

    while type(ATYPE) in (Typedef, TypeDecl):
        ATYPE = ATYPE.type

    if type(ATYPE) is ArrayDecl:
        size = 1
        while type(ATYPE) is ArrayDecl:
            size *= int(ATYPE.dim.value)
            ATYPE = ATYPE.type
        write_c("memcpy({0}, {1}, sizeof({2}));"
                .format(A, B, size))
        return
    
    elif isPodType(ATYPE):
        write_c("{0} = {1};".format(B, A));
        return
    elif isPointer(ATYPE):
        write_c("if (({0} = {1}) != NULL) {{".format(B, A))
        write_c("{0} = malloc(sizeof(*{0}));".format(B))
        struct_copy_rec("(*{0})".format(A), deref(ATYPE),
                        "(*{0})".format(B), deref(BTYPE))
        write_c("}")

    if type(ATYPE) in [ Struct, Union ]:
        for F in fields(ATYPE):
            struct_copy_rec("({0}).{1}".format(A, F.name), F.type, \
                            "({0}).{1}".format(B, F.name), F.type)

##if askIsArray(A):
##            L = askArrayLengthField()
##            if isPodType(deref(ATYPE)):
##                write_c("memcpy({0}, {1}, {0}->{2} * sizeof({0}));"
##                                    .format(A, B, L ))
##            else:
##                write_c("for (n = 0; n < {0}; ++n) {{\n".format(L))
##                struct_copy_rec(A, ATYPE, B, BTYPE)
##                write_c("}")
##        else:

def struct_copy(A, ATYPE, BTYPE):
    write_c("{2} struct_copy({0} {1})\n{{"
                .format(ATYPE, A, BTYPE))
    write_c("{0} {1};".format(BTYPE, "X"))
    struct_copy_rec(A, gettype(ATYPE), "X", gettype(BTYPE))
    write_c("return({0});".format("X"))
    write_c("}")

loadtypedefs()
hook[("char *", "char *")] = "strdup"
struct_copy("a", "PA", "PA");
file 
#ast.show()
#struct_copy("pqs", "WSAQUERYSET", "pqsw", "WSAQUERYSETW");


