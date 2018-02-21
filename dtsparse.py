#!/usr/bin/env python3

# ./out/target/product/msm8937_64/obj/KERNEL_OBJ/scripts/dtc/dtc -I dtb -O dts ./out/target/product/msm8937_64/obj/KERNEL_OBJ/arch/arm64/boot/dts/qcom/zte-msm8940-pmi8940-vita.dtb

from argparse import ArgumentParser
import re
import string


class Node():
        def __init__(self):
                self.__attributes = {}
                self.__name = ''
                self.__subnodes = []
        def AddAttribute(self, key, value = ''):
                self.__attributes[key] = value
        def AddStatement(self, statement):
                """
                        statement is stripped and without ';' character
                """
                if not statement:
                        return
                with_equal_char = 1
                try:
                        i = statement.index('=')
                except:
                        with_equal_char = 0
                if with_equal_char:
                        self.AddAttribute(statement[0:i].strip(), statement[i+1:].strip())
                else:

                        self.AddAttribute(statement.strip(), '')
        def SetName(self, name):
                self.__name = name
        def Name(self):
                if not self.__name:
                        raise ValueError('node name is not set yet')
                return self.__name
        def AddSubNode(self, node):
                if not isinstance(node, Node):
                        raise TypeError('node must be instance of Node')
                self.__subnodes.append(node)
        def dump(self, deepth = 0):
                indent_string = '\t'* deepth
                print(indent_string, self.Name(), ' {', sep='')
                for key in self.__attributes:
                        if self.__attributes[key]:
                                print(indent_string, '\t', key, ' = ', self.__attributes[key], ';', sep='')
                        else:
                                print(indent_string, '\t', key, ';', sep='')
                for node in self.__subnodes:
                        print()
                        node.dump(deepth+1)
                print(indent_string, '};', sep='')

def gpio_parser_by_handle(node, gpio_handle):
        if not isinstance(node, Node):
                raise TypeError('node must be instance of Node')

def node_parser(contents, start_pos, node_name = None):
        """
        Parse node infomation, with starting '{' and ending '};', without node name

        start_pos
        |
        {
                attribute1;
                subnode {
                };
                subnode {
                };
        };
         |
        end_pos

        Return (node, pos), pos is the end pos of node
        """
        print(node_name)
        node = Node()
        if node_name:
                node.SetName(node_name)
        node_deepth = -1 # the main node deepth is 0, subnode deepth is greater than 0
        length = len(contents)
        prepos = pos = start_pos  # contents[prepos:pos] is used to check an attribute statement
        i = start_pos
        while i < length:
                if node_deepth < 0 and prepos != start_pos:
                        while i < length and contents[i] != ';':
                                i += 1
                        break
                elif contents[i] == '{': #a node start position
                        node_deepth += 1
                        prepos = i + 1
                        if node_deepth == 1: #parse the first level sub node
                                #get node name
                                j = i -1
                                while j >= 0 and contents[j] not in [';', '{']:
                                        j -= 1
                                name = contents[j:i].translate(str.maketrans('', '', ';{')).strip()
                                subnode, pos = node_parser(contents, i, name)
                                node.AddSubNode(subnode)
                                i = pos
                elif contents[i] == '}':
                        node_deepth -= 1
                        prepos = i + 1
                elif contents[i] == ';':
                        if node_deepth == 0:
                                pos = i
                                node.AddStatement(contents[prepos:pos].strip())
                                prepos = i + 1
                i += 1
        return (node, i)
def dts_parser(filename):
        with open(filename, 'r') as fd:
                contents = fd.read()

        for i in range(len(contents)):
                if contents[i] == '{': #parse / node
                        #get node name
                        j = i -1
                        while j >= 0 and contents[j] not in [';', '{']:
                                j -= 1
                        name = contents[j:i].translate(str.maketrans('', '', ';{')).strip()
                        root, pos = node_parser(contents, i, name)
                        break
        return root

if __name__ == "__main__":
        parser = ArgumentParser(description = "Parse gpio configuration in dts file")
        parser.add_argument("-f", metavar='dtsfile', nargs=1, type=str, required=True, help = "parse dts file")
        command = parser.parse_args()

        RootNode = dts_parser(command.f[0])
        RootNode.dump()
