from __future__ import print_function
import new
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
    ret = ''
    for item in inp:
        if isinstance(item, str):
            ret += o(item)
        else:
            ret += s(item)
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
    code = func.func_code
    if line < 0:
        lineno = code.co_firstlineno
        line = -line
    else:
        lineno = 0
    co_lnotab = code.co_lnotab
    addr = 0
    for addr_incr, line_incr in zip(co_lnotab[::2], co_lnotab[1::2]):
        addr += ord(addr_incr)
        lineno += ord(line_incr)
        if lineno == line:
            return addr
    return None


# TODO support scanning the insert_code as well.. currently does not (fix this if you want to make this a generic insert code)
def insertbytecode(co_code, addr, insert_code):
    newcode = co_code[:addr] + insert_code + co_code[addr:]
    insert_len = len(insert_code)
    n = len(newcode)
    i = 0
    fixedcode = ''
    while i < n:
        c = newcode[i]
        fixedcode += c
        op = ord(c)
        i += 1
        if op >= dis.HAVE_ARGUMENT:
            oparg = ord(newcode[i]) + ord(newcode[i + 1]) * 256
            i += 2
            if op in dis.hasjrel:
                target = i + oparg
                if i < addr and target >= addr:
                    oparg += insert_len
            elif op in dis.hasjabs:
                target = oparg
                if i < addr and target >= addr:
                    oparg += insert_len
                elif i > addr + insert_len and target >= addr:
                    oparg += insert_len
            fixedcode += s(oparg)
    return fixedcode


# TODO insert_len limited to 256 for now.. (fix this if you want to make this a generic insert code)
def fixlines(co_lnotab, insert_addr, insert_len):
    byte_increments = [ord(c) for c in co_lnotab[0::2]]
    line_increments = [ord(c) for c in co_lnotab[1::2]]
    new_lnotab = ''
    lineno = 0
    addr = 0
    for byte_incr, line_incr in zip(byte_increments, line_increments):
        addr += byte_incr
        lineno += line_incr
        if addr > insert_addr:
            byte_incr += insert_len
        new_lnotab += chr(byte_incr) + chr(line_incr)
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
    global hookpointcounter
    hookpoints[hookpointcounter] = insert_func
    code = func.func_code
    newconsts, noneindex, minusoneindex, hookpointindex = getoraddtotuple(code.co_consts, None, -1, hookpointcounter)
    newnames, replaceindex, runhookpointindex = getoraddtotuple(code.co_names, __name__, 'run_hookpoint')
    if with_state:
        newnames, localsindex, globalsindex = getoraddtotuple(newnames, 'locals', 'globals')
        pdbtracecode = createbytecode('LOAD_CONST', minusoneindex, 'LOAD_CONST', noneindex, 'IMPORT_NAME', replaceindex, 'LOAD_ATTR', runhookpointindex, 'LOAD_CONST', hookpointindex, 'LOAD_GLOBAL', localsindex, 'CALL_FUNCTION', 0, 'LOAD_GLOBAL', globalsindex, 'CALL_FUNCTION', 0, 'CALL_FUNCTION', 3, 'POP_TOP')
    else:
        pdbtracecode = createbytecode('LOAD_CONST', minusoneindex, 'LOAD_CONST', noneindex, 'IMPORT_NAME', replaceindex, 'LOAD_ATTR', runhookpointindex, 'LOAD_CONST', hookpointindex, 'CALL_FUNCTION', 1, 'POP_TOP')
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
    newfunc = new.code(code.co_argcount, code.co_nlocals, newstacksize, code.co_flags, newcode, newconsts, newnames, code.co_varnames, code.co_filename, code.co_name, code.co_firstlineno, newlnotab, code.co_freevars, code.co_cellvars)
    # TODO make this thread safe (index returning number)
    hookpointcounter += 1
    if func.func_code in mapping:
        mapping[newfunc] = mapping[func.func_code]
    else:
        mapping[newfunc] = func.func_code
    origin[hookpointcounter - 1] = mapping[newfunc]
    func.func_code = newfunc
    return hookpointcounter - 1
