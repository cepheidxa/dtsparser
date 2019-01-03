#!/usr/bin/env python3

import unittest
import fnmatch
import os
import dtsparser
from builtins import isinstance
import re

class NodeTest(unittest.TestCase):
    def test_name(self):
        node = dtsparser.Node()
        with self.assertRaises(ValueError):
            node.name
        with self.assertRaises(ValueError):
            node.name = 35
        node.name = 'name@4515'
        self.assertEqual(node.name, 'name@4515')
        with self.assertRaises(ValueError):
            node.name = 'name@45'

    def test_addstatement(self):
        node = dtsparser.Node()
        node.addstatement('compatible = "shared-dma-pool";')
        self.assertEqual(len(node.attributes), 1)
        node.addstatement('reusable;')
        self.assertEqual(len(node.attributes), 2)
        node.addstatement('alignment = <0x0 0x400000>;')
        self.assertEqual(len(node.attributes), 3)
        node.addstatement('linux,phandle = <0x100>;')
        self.assertEqual(len(node.attributes), 4)
        node.addstatement('reg = <0x0 0x90000000 0x0 0x1400000>;')
        self.assertEqual(len(node.attributes), 5)
        self.assertEqual(node.attributes['compatible'], '"shared-dma-pool"')
        self.assertEqual(node.attributes['reusable'], '')
        self.assertEqual(node.attributes['alignment'], '<0x0 0x400000>')
        self.assertEqual(node.attributes['linux,phandle'], '<0x100>')
        self.assertEqual(node.attributes['reg'], '<0x0 0x90000000 0x0 0x1400000>')
        self.assertEqual(len(node.attributes), 5)
        node.addstatement('compatible = "shared-dma-pool2"')
        self.assertEqual(node.attributes['compatible'], '"shared-dma-pool2"')
        node.addstatement('compatible = "shared-dma-pool3";\n')
        self.assertEqual(node.attributes['compatible'], '"shared-dma-pool3"')
        node.addstatement('reusable2')
        self.assertEqual(node.attributes['reusable2'], '')
        node.addstatement('reusable3;\n')
        self.assertEqual(node.attributes['reusable3'], '')
        with self.assertRaises(KeyError):
            self.assertEqual(node.attributes['reusableaaa'], '')

    def test_isDisabled(self):
        node = dtsparser.Node()
        node.addstatement('compatible = "shared-dma-pool";')
        node.addstatement('reusable;')
        node.addstatement('alignment = <0x0 0x400000>;')
        node.addstatement('linux,phandle = <0x100>;')
        node.addstatement('reg = <0x0 0x90000000 0x0 0x1400000>;')
        self.assertFalse(node.isDisabled())
        node.addstatement('status = "ok";')
        self.assertEqual(node.attributes['status'], '"ok"')
        self.assertFalse(node.isDisabled())
        node.addstatement('status = "okay";')
        self.assertEqual(node.attributes['status'], '"okay"')
        self.assertFalse(node.isDisabled())
        node.addstatement('status = "disabled";')
        self.assertEqual(node.attributes['status'], '"disabled"')
        self.assertTrue(node.isDisabled())

    def test_addsubnode(self):
        root = dtsparser.Node()
        node1 = dtsparser.Node()
        node2 = dtsparser.Node()
        node3 = dtsparser.Node()
        node11 = dtsparser.Node()
        node12 = dtsparser.Node()
        node111 = dtsparser.Node()
        node21 = dtsparser.Node()
        node31 = dtsparser.Node()
        root.addsubnode(node1)
        root.addsubnode(node2)
        root.addsubnode(node3)
        node1.addsubnode(node11)
        node1.addsubnode(node12)
        node11.addsubnode(node111)
        node2.addsubnode(node21)
        node3.addsubnode(node31)
        with self.assertRaises(TypeError):
            root.addsubnode('aaa')
        with self.assertRaises(TypeError):
            root.addsubnode('None')
        self.assertEqual(root.subnodes, [node1, node2, node3])
        self.assertEqual(node1.subnodes, [node11, node12])
        self.assertEqual(node11.subnodes, [node111])
        self.assertEqual(node2.subnodes, [node21])
        self.assertEqual(node3.subnodes, [node31])
        self.assertEqual(node111.subnodes, [])
        self.assertEqual(node21.subnodes, [])
        self.assertEqual(node31.subnodes, [])
        
    def test_dump(self):
        node = dtsparser.Node()
        with self.assertRaises(ValueError):
            node.dump()
        node.name = 'name@45'
        dumpmsg = 'name@45 {\n'
        dumpmsg_tailer = '};\n'
        self.assertEqual(node.dump(), dumpmsg + dumpmsg_tailer)
        node.addstatement('compatible = "shared-dma-pool";')
        dumpmsg += '\tcompatible = "shared-dma-pool";\n'
        self.assertEqual(node.dump(), dumpmsg + dumpmsg_tailer)
        node.addstatement('reusable;')
        dumpmsg += '\treusable;\n'
        self.assertEqual(node.dump(), dumpmsg + dumpmsg_tailer)
        node.addstatement('alignment = <0x0 0x400000>;')
        dumpmsg += '\talignment = <0x0 0x400000>;\n'
        self.assertEqual(node.dump(), dumpmsg + dumpmsg_tailer)
        node.addstatement('linux,phandle = <0x100>;')
        dumpmsg += '\tlinux,phandle = <0x100>;\n'
        self.assertEqual(node.dump(), dumpmsg + dumpmsg_tailer)
        node.addstatement('reg = <0x0 0x90000000 0x0 0x1400000>;')
        dumpmsg += '\treg = <0x0 0x90000000 0x0 0x1400000>;\n'
        self.assertEqual(node.dump(), dumpmsg + dumpmsg_tailer)
        
        node = dtsparser.Node()
        node.name = 'name'
        node.addstatement('status = "disabled";')
        self.assertTrue(node.isDisabled())
        dumpmsg = node.dump()
        self.assertEqual(dumpmsg, '')
        dumpmsg_with_disabled = node.dump(withdisabled=True)
        self.assertEqual(dumpmsg_with_disabled, 'name {\n\tstatus = "disabled";\n};\n')

        subnode = dtsparser.Node()
        subnode.name = 'name1'
        subnode.addstatement('status = "disabled";')
        self.assertTrue(subnode.isDisabled())
        node.addsubnode(subnode)
        dumpmsg = node.dump()
        self.assertEqual(dumpmsg, '')
        dumpmsg_with_disabled = node.dump(withdisabled=True)
        self.assertEqual(dumpmsg_with_disabled, 'name {\n\tstatus = "disabled";\n\n\tname1 {\n\t\tstatus = "disabled";\n\t};\n};\n')


class DtsInfoTest(unittest.TestCase):
    pass


class DtsParserTest(unittest.TestCase):
    def setUp(self):
        self.__dtsfiles = []
        for file in os.listdir('.'):
            if fnmatch.fnmatch(file, '*.dts'):
                self.__dtsfiles.append(file)
    def test_dts_parser(self):
        for file in self.__dtsfiles:
            fd = open(file, 'r')
            
            with self.assertRaises(ValueError):
                dtsparser.dts_parser(None, None)
            with self.assertRaises(ValueError):
                dtsparser.dts_parser(file, fd)
            
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

            contents_by_filename_with_disabled = node_by_filename.dump(withdisabled=True)
            contents_by_fd_with_disabled = node_by_fd.dump(withdisabled=True)
            
            self.assertTrue(isinstance(contents_by_filename_with_disabled, str))
            self.assertTrue(isinstance(contents_by_fd_with_disabled, str))
            self.assertNotEqual(contents_by_filename_with_disabled, contents_by_filename)
            self.assertGreater(len(contents_by_filename), 0)
            self.assertGreater(len(contents_by_fd), 0)
            self.assertEqual(contents_by_fd_with_disabled, contents_by_fd_with_disabled)
            
            resultfile = re.sub(re.compile('\.dts$'), '.txt', file)
            with open(resultfile, 'r') as fd:
                resultfilecontents = fd.read()
            self.assertEqual(contents_by_filename_with_disabled, resultfilecontents)
        

if __name__ == '__main__':
    unittest.main()