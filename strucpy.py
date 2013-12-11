#!/usr/bin/python2.7

from pycparserext.ext_c_parser import GnuCParser
from pycparser import parse_file
from pycparser.c_parser import ParseError
from pycparser.c_ast import *
from textwrap import *

ast = None
hookDict = []
output = None
header = None
gcp = GnuCParser()

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
    global output
    output.write("\n".join(wrap(s, break_long_words=False)))
    output.write("\n")

def write_h(s):
    global header
    header.write(s + "\n")

def askIsArray(FIELD):
    msg = "Is field \"{0}\" an array?".format(FIELD)
    return True if raw_input("%s (y/N) " % msg).lower() == 'y' else False

def askArrayLengthField():
    print "Enter field determing array length: "
    return raw_input()

def isStdType(NAME):
    return NAME in ("int", "float", "void", "char", "signed",
                    "unsigned", "auto", "short", "long", "wchar_t")

def isPodType(TYPE):
    """ Check type for being plain-old-data type, which can be
    just copied with memcpy"""

    if hasattr(TYPE, "POD"):
        return TYPE.POD

    t = type(TYPE)
    result = False

    if t in (Typedef, TypeDecl, Decl, ArrayDecl):
        result = isPodType(TYPE.type)
    elif t is Struct:
        result = all(map(isPodType, fields(TYPE)))
    elif t is IdentifierType:
        result = all(map(
            lambda n : isStdType(n) or isPodType(gettype(n))
                , TYPE.names));
    elif t in (Constant, Union):
        result = True

    TYPE.POD = result
    return result;

def isPointer(TYPE):
    return type(TYPE) is PtrDecl 
#               or hasattr(TYPE, "type") \
#               and type(TYPE.type) is PtrDecl;

def deref(TYPE):
    """ Return subnode if pointer, grandchild if sub is pointer """
    if type(TYPE) is PtrDecl:
        return TYPE.type
#    elif hasattr(TYPE, "type") and type(TYPE.type) is PtrDecl:
#        return TYPE.type.type
    return None

def fields(TYPE):
    return TYPE.decls if type(TYPE) is Struct else []

def sethook(ATYPE, BTYPE, FUNC):
    hookDict.append((ctype(ATYPE), ctype(BTYPE), FUNC, ));

def gethook(ATYPE, BTYPE, NAME):
    for h in hookDict:
        if isCtypeEq(ATYPE, h[0]) and isCtypeEq(BTYPE, h[1]):
            return "%s(%s)" % (h[2], NAME)
    return None

def ctype(TYPESTR):
    global gcp
    a = gettype(TYPESTR)
    if not a:
        a = gcp.parse(TYPESTR + " X;").ext[0].type
    return a

def isCtypeEq(ATYPE, BTYPE):
    t = type(ATYPE)
    if t is type(BTYPE):
        if t in (Typedef, TypeDecl, Decl, ArrayDecl, PtrDecl):
            return isCtypeEq(ATYPE.type, BTYPE.type)
        elif t is Struct:
            return all(map(isCtypeEq, fields(ATYPE), fields(BTYPE) ))
        elif t is IdentifierType:
            return ATYPE.names == BTYPE.names;
        elif t is (Constant,):
            return ATYPE.value == BTYPE.value
    return False 

def struct_copy_rec(A, ATYPE, B, BTYPE):
    h = gethook(ATYPE, BTYPE, A)
    if h:
        write_c("%s = %s;" % (B, h))
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

    elif isPodType(ATYPE):
        write_c("{0} = {1};".format(B, A));
    elif isPointer(ATYPE) and type(deref(ATYPE)) is TypeDecl and \
        type(deref(ATYPE).type) is Struct and not isPodType(deref(ATYPE).type):
#pointer to non-POD struct, use "->"
        write_c("if (({0} = {1}) != NULL)\n{{".format(B, A))
        write_c("{0} = malloc(sizeof(*{0}));".format(B))
        ATYPE = deref(ATYPE).type
        for F in fields(ATYPE):
            struct_copy_rec("{0}->{1}".format(A, F.name), F.type, \
                            "{0}->{1}".format(B, F.name), F.type)
        write_c("}")
    elif isPointer(ATYPE):
        write_c("if (({0} = {1}) != NULL)\n{{".format(B, A))
        write_c("{0} = malloc(sizeof(*{0}));".format(B))

        struct_copy_rec("(*{0})".format(A), deref(ATYPE),
                        "(*{0})".format(B), deref(BTYPE))
        write_c("}")
    elif type(ATYPE) is Struct:
        for F in fields(ATYPE):
            struct_copy_rec("{0}.{1}".format(A, F.name), F.type, \
                            "{0}.{1}".format(B, F.name), F.type)

#TODO: fix array support
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

def struct_copy_proto(A, ATYPE, BTYPE):
	return "{2} struct_copy_{0}_{2}({0} {1})".format(ATYPE, A, BTYPE)

def struct_copy(ATYPE, BTYPE):
    write_c(struct_copy_proto("s", ATYPE, BTYPE))
    write_c("{")
    write_c("{0} {1};".format(BTYPE, "X"))
    struct_copy_rec("s", gettype(ATYPE), "X", gettype(BTYPE))
    write_c("return({0});".format("X"))
    write_c("}\n\n")
    write_h(struct_copy_proto("s", ATYPE, BTYPE) + ";")

def processFiles(FILES):
	global ast, output, header
	output = file("strucpy.c", "w")
	header = file("strucpy.h", "w")
	write_c("#include \"strucpy.h\"")
	write_c("#include <stdlib.h>")
	write_c("#include <string.h>")

	for f in FILES:
		try:
			ast = parse_file(f, parser=gcp)
		except ParseError as e:
			print "Parse error: " + e.message
                        break

                sethook("char *", "char *", "strdup")

                #TODO: hook any types loaded in AST
                #sethook("LPSTR", "LPSTR", "strdup")

		write_h("#include \"" + f + "\"")
		struct_copy("LPWSAQUERYSETA", "LPWSAQUERYSETA");
		struct_copy("PA", "PA");

	output.close()
	header.close()

processFiles(("example.h",))

#a = ctype("const int *")
#b = ctype("int *")
#print a == b
#print isCtypeEq(a, b)

#processFiles(("/media/usb3/media/Src/wine/wine/include/ws2def.h",))

