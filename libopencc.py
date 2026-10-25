#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:
'''wrapper of libopencc

opencc is a library for converting character between traditional chinese and simplified chinese.

@author: Jiahua Huang <jhuangjiahua@gmail.com>
@license: LGPLv3+
@see: opencc
'''

import ctypes
import ctypes.util
import sys

libc = ctypes.CDLL(ctypes.util.find_library('c'))
opencc = ctypes.CDLL(ctypes.util.find_library('opencc'))
opencc.opencc_open.argtypes = [ctypes.c_char_p]
opencc.opencc_open.restype = ctypes.c_void_p
opencc.opencc_convert_utf8.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
opencc.opencc_convert_utf8.restype = ctypes.c_void_p
libc.free.argtypes = [ctypes.c_void_p]
opencc.opencc_convert_utf8_free.argtypes = [ctypes.c_void_p]
od = opencc.opencc_open(b's2t.json')
if od in (None, ctypes.c_void_p(-1).value):
    raise RuntimeError('Unable to open OpenCC s2t.json')

def convert(text):
    '''convert simplified chinese to traditional chinese
    '''
    if isinstance(text, str):
        text = text.encode('utf8')
    ret = opencc.opencc_convert_utf8(od, text, -1)
    if not ret:
        raise RuntimeError('OpenCC conversion failed')
    try:
        return ctypes.string_at(ret).decode('utf8')
    finally:
        opencc.opencc_convert_utf8_free(ret)


if __name__=="__main__":
    if sys.argv[1:]:
        text = ' '.join(sys.argv[1:])
        pass
    else:
        text = sys.stdin.read()
        pass
    print(convert(text))
