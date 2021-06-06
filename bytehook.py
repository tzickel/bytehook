import types
import dis
import struct

__version__ = "0.0.1"

# TODO add docstring explanations
# TODO add support for python 3 and pypy
# TODO how to handle flags such as CO_FUTURE_UNICODE_LITERALS (check code.h)
# TODO reloading this clears all the vars... maybe make this object oriented ?
# TODO currently cannot remove the hookpoint completely


def s(short):
    # opcode arguments are always unsigned short
    return struct.pack('H', short)


def o(s):
    return chr(dis.opmap[s])


def createbytecode(*inp):
    ret = bytes()
    for item in inp:
        if isinstance(item, str):
            ret += bytes({dis.opmap[item]})
        else:
            ret += bytes({item})
    return ret


def getoraddtotuple(t, *names):
    indexs = []
    tmp = list(t)
    added = False
    for name in names:
        try:
            ind = tmp.index(name)
            indexs.append(ind)
        except ValueError:
            added = True
            tmp.append(name)
            indexs.append(len(tmp) - 1)
    if added:
        t = tuple(tmp)
    indexs.insert(0, t)
    return indexs


def line2addr(func, line):
    code = func.__code__
    if line < 0:
        lineno = code.co_firstlineno
        line = -line
    else:
        lineno = 0
    co_lnotab = code.co_lnotab
    addr = 0
    for addr_incr, line_incr in zip(co_lnotab[::2], co_lnotab[1::2]):
        addr += addr_incr
        lineno += line_incr
        if lineno == line:
            return addr
    return None

def unpack_op(bytecode):
    for i in range(0, len(bytecode), 2):
        opcode = bytecode[i]
        if opcode >= dis.HAVE_ARGUMENT:
            oparg = bytecode[i + 1]
        else:
            oparg = None
        yield (i, opcode, oparg)

# TODO support scanning the insert_code as well.. currently does not (fix this if you want to make this a generic insert code)
def insertbytecode(co_code, addr, insert_code):
    newcode = co_code[:addr] + insert_code + co_code[addr:]
    insert_len = len(insert_code)
    fixedcode = bytes()
    extended_arg = 0

    for offset, opcode, oparg in unpack_op(newcode):
        fixedcode += bytes({opcode})
        if oparg is not None:
            oparg_ext = 0
            i = extended_arg
            while i:
                """
                    possible extended_arg                          +                +                +
                    fixedcode = |op1|arg1|op2|arg2|...|op(n-3)|arg(n-3)|op(n-2)|arg(n-2)|op(n-1)|arg(n-1)|opn|
                    index                                         -6               -4               -2    -1
                """
                oparg_ext += (oparg_ext << 8) + fixedcode[0 - 2 * i]
                i -= 1

            if opcode in dis.hasjrel:
                target = offset + (oparg_ext << 8) + oparg + 2
                if offset < addr and target >= addr:
                    target += insert_len
                    oparg = target - 2 - offset
                    if oparg > 2**32 - 1:
                        raise Exception("Argument exceeds the maximum value")
                    else:
                        tmp = bytes()
                        while oparg > 255:
                            # get EXTENDED_ARG's argument by bit manipulation
                            tmp = bytes({dis.EXTENDED_ARG}) + bytes({oparg & 0b11111111}) + tmp
                            oparg = oparg >> 8
                        # remove the old part from fixedcode and concat the new part
                        fixedcode = fixedcode[:0-2*extended_arg-1] + tmp + bytes({opcode})
            elif opcode in dis.hasjabs:
                target = (oparg_ext << 8) + oparg
                if offset < addr and target >= addr or offset >= addr + insert_len and target >= addr:
                    target += insert_len
                    oparg = target
                    if oparg > 2**32 - 1:
                        raise Exception("Argument exceeds the maximum value")
                    else:
                        tmp = bytes()
                        while oparg > 255:
                            # get EXTENDED_ARG's argument by bit manipulation
                            tmp = bytes({dis.EXTENDED_ARG}) + bytes({oparg & 0b11111111}) + tmp
                            oparg = oparg >> 8
                        # remove the old part from fixedcode and concat the new part
                        fixedcode = fixedcode[:0-2*extended_arg-1] + tmp + bytes({opcode})

            fixedcode += bytes({oparg})
        else:
            fixedcode += bytes({0})

        extended_arg = extended_arg + 1 if opcode == dis.EXTENDED_ARG else 0

    return fixedcode


# TODO insert_len limited to 256 for now.. (fix this if you want to make this a generic insert code)
def fixlines(co_lnotab, insert_addr, insert_len):
    byte_increments = [c for c in co_lnotab[0::2]]
    line_increments = [c for c in co_lnotab[1::2]]
    new_lnotab = bytes()
    lineno = 0
    addr = 0
    for byte_incr, line_incr in zip(byte_increments, line_increments):
        addr += byte_incr
        lineno += line_incr
        if addr >= insert_addr:
            byte_incr += insert_len
        new_lnotab += bytes({byte_incr}) + bytes({line_incr})
    return new_lnotab


hookpoints = {}
disabledhookpoints = {}
hookpointcounter = 0
mapping = {}
origin = {}


def run_hookpoint(num, _locals=None, _globals=None):
    if num in hookpoints:
        hookpoints[num](_locals, _globals)


def disable_hookpoint(num):
    if num not in hookpoints:
        raise Exception('Breakpoint not enabled')
    disabledhookpoints[num] = hookpoints[num]
    del hookpoints[num]


def enable_hookpoint(num):
    if num not in disabledhookpoints:
        raise Exception('Breakpoint not disabled')
    hookpoints[num] = disabledhookpoints[num]
    del disabledhookpoints[num]


def change_hookpoint(num, func):
    if num in hookpoints:
        hookpoints[num] = func
    elif num in disabledhookpoints:
        disabledhookpoints[num] = func
    else:
        raise Exception('Breakpoint not found')


def list_hookpoints():
    for k, v in origin.iteritems():
        if k in hookpoints:
            print('E', k, v)
        else:
            print('D', k, v)


def runpdb(_locals=None, _globals=None):
    import pdb
    pdb.set_trace()


# TODO check that closures and nested functions work here as well
def hook(func, lineno=None, insert_func=runpdb, with_state=False):
    import pdb
    global hookpointcounter
    hookpoints[hookpointcounter] = insert_func
    code = func.__code__
    newconsts, noneindex, zeroindex, hookpointindex = getoraddtotuple(code.co_consts, None, 0, hookpointcounter)
    newnames, replaceindex, runhookpointindex = getoraddtotuple(code.co_names, __name__, 'run_hookpoint')
    if with_state:
        newnames, localsindex, globalsindex = getoraddtotuple(newnames, 'locals', 'globals')
        pdbtracecode = createbytecode('LOAD_CONST', zeroindex, 'LOAD_CONST', noneindex, 'IMPORT_NAME', replaceindex, 'LOAD_ATTR', runhookpointindex, 'LOAD_CONST', hookpointindex, 'LOAD_GLOBAL', localsindex, 'CALL_FUNCTION', 0, 'LOAD_GLOBAL', globalsindex, 'CALL_FUNCTION', 0, 'CALL_FUNCTION', 3, 'POP_TOP', 0)
    else:
        pdbtracecode = createbytecode('LOAD_CONST', zeroindex, 'LOAD_CONST', noneindex, 'IMPORT_NAME', replaceindex, 'LOAD_ATTR', runhookpointindex, 'LOAD_CONST', hookpointindex, 'CALL_FUNCTION', 1, 'POP_TOP', 0)
    if lineno is None:
        newcode = insertbytecode(code.co_code, 0, pdbtracecode)
        newlnotab = fixlines(code.co_lnotab, 0, len(pdbtracecode))
    else:
        addr = line2addr(func, lineno)
        if addr is None:
            raise Exception('Line not found')
        newcode = insertbytecode(code.co_code, addr, pdbtracecode)
        newlnotab = fixlines(code.co_lnotab, addr, len(pdbtracecode))
    # TODO is this correct ?
    newstacksize = code.co_stacksize + 4 if with_state else 2
    newfunc = types.CodeType(code.co_argcount, code.co_kwonlyargcount, code.co_nlocals, newstacksize, code.co_flags, newcode, newconsts, newnames, code.co_varnames, code.co_filename, code.co_name, code.co_firstlineno, newlnotab, code.co_freevars, code.co_cellvars)
    pdb.set_trace()
    # TODO make this thread safe (index returning number)
    hookpointcounter += 1
    if func.__code__ in mapping:
        mapping[newfunc] = mapping[func.__code__]
    else:
        mapping[newfunc] = func.__code__
    origin[hookpointcounter - 1] = mapping[newfunc]
    func.__code__ = newfunc
    return hookpointcounter - 1
