#!/usr/bin/env python3

import unittest
import fnmatch
import os
import dtsparser
from builtins import isinstance

class NodeTest(unittest.TestCase):
    def setUp(self):
        self.__dtsfiles = []
        for file in os.listdir('.'):
            if fnmatch.fnmatch(file, '*.dts'):
                self.__dtsfiles.append(file)

    def test_name(self):
        node = dtsparser.Node()
        with self.assertRaises(ValueError):
            node.name
        node.name = 'name@4515'
        self.assertEqual(node.name, 'name@4515')
        with self.assertRaises(ValueError):
            node.name = 'name@45'

    def test_addstatement(self):
        node = dtsparser.Node()
        node.addstatement('compatible = "shared-dma-pool";')
        node.addstatement('reusable;')
        node.addstatement('alignment = <0x0 0x400000>;')
        node.addstatement('linux,phandle = <0x100>;')
        node.addstatement('reg = <0x0 0x90000000 0x0 0x1400000>;')
        self.assertEqual(node.attributes['compatible'], '"shared-dma-pool";')
        self.assertEqual(node.attributes['reusable'], '')
        self.assertEqual(node.attributes['alignment'], '<0x0 0x400000>;')
        self.assertEqual(node.attributes['linux,phandle'], '<0x100>;')
        self.assertEqual(node.attributes['reg'], '<0x0 0x90000000 0x0 0x1400000>;')

    def test_Node(self):
        for file in self.__dtsfiles:
            fd = open(file, 'r')
            
            self.assertRaises(ValueError, dtsparser.dts_parser, None, None)
            self.assertRaises(ValueError, dtsparser.dts_parser, file, fd)
            
            node_by_filename = dtsparser.dts_parser(file, None)
            node_by_fd = dtsparser.dts_parser(None, fd)
            contents_by_filename = node_by_filename.dump()
            contents_by_fd = node_by_fd.dump()
            
            self.assertTrue(isinstance(contents_by_filename, str))
            self.assertTrue(isinstance(contents_by_fd, str))
            self.assertGreater(len(contents_by_filename), 0)
            self.assertGreater(len(contents_by_fd), 0)
            self.assertEqual(contents_by_filename, contents_by_fd)
            self.assertFalse(fd.closed)
            fd.close()

    def test_dump(self):
        node = dtsparser.Node()
        with self.assertRaises(ValueError):
            node.dump()
        node.name = 'name@45'
        dumpmsg = 'name@45 {\n};\n'
        self.assertEqual(node.dump(), dumpmsg)
        

if __name__ == '__main__':
    unittest.main()