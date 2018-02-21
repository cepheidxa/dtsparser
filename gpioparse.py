#!/usr/bin/env python3

# ./out/target/product/msm8937_64/obj/KERNEL_OBJ/scripts/dtc/dtc -I dtb -O dts ./out/target/product/msm8937_64/obj/KERNEL_OBJ/arch/arm64/boot/dts/qcom/zte-msm8940-pmi8940-vita.dtb

from argparse import ArgumentParser
import re


class Node():
        """ parse contents as follows
                
                nodename {
                        attribute1 = value1;
                        attribute2 = value2;
                        subnode1 {
                        };
                        subnode2 {
                        };
                        attribute3 = value3;
                }
        """
        def __init__(self, contents, deepth = 0):
                self.__contents = contents
                self.__name = re.compile('\S+').search(contents).group(0)
                self.__attributes = self.attributes()
                self.__subnodes = self.find_sub_nodes()
                self.__deepth = deepth
        def attributes(self):
                """
                        self.__contents = 'config { pins = "gpio24"; drive-strength = <0x2>; bias-pull-down; };'
                        Return: {'pins': '"gpio24"', 'drive-strength':'<0x2>', 'bias-pull-down':''}
                """
                ret = {}
                main_node_context = 0
                contents = re.sub(re.compile('[^;]*{'), '{', self.__contents)
                contents_list = []
                for i in range(len(contents)):
                        if contents[i] == '{':
                                main_node_context += 1
                                continue
                        elif contents[i] == '}':
                                main_node_context -= 1
                                continue
                        if main_node_context == 1:
                                contents_list.append(contents[i])
                                
                contents = ''.join(contents_list)
                contents = re.sub(re.compile(';\s*;'), ';', contents)
                statements = re.findall(re.compile('[^;]+;'), contents)
                for item in statements:
                        v = re.findall(re.compile('[^;=]+'), item)
                        if len(v) == 2:
                                ret[v[0].strip()] = v[1].strip()
                        else:

                                ret[v[0].strip()] = ''
                return ret
        def name(self):
                return self.__name
        def find_sub_nodes_pos(self):
                """
                        find sub node position, whit with starting withspace and ending ; punctuation

                        self.__contents = 'name { a1 = v1; name { a = v; a= v}; a2 = v2;}'
                        subnode is ' name { a = v; a= v};'
                        self.__contents[14] is ';'
                        self.__contents[35] is ';'        
                        return: [(15, 35)]
                        
                        self.__contents = 'cpu-map { cluster0 { core0 { cpu = <0x2>; }; core1 { cpu = <0x3>; }; core2 { cpu = <0x4>; }; core3 { cpu = <0x5>; }; }; cluster1 { core0 { cpu = <0x6>; }; core1 { cpu = <0x7>; }; core2 { cpu = <0x8>; }; core3 { cpu = <0x9>; }; }; }'
                        subnode is ' cluster0 {  ..... };' ' cluster1 {  ..... };'
                        self.__contents[8] is '{'
                        self.__contents[103] is ';'        
                        return: [(15, 103), (113, 158)]
                """
                subnodes = []
                node_start = -1
                for i in range(len(self.__contents)):
                        if self.__contents[i] == '{':
                                node_start += 1
                                if node_start == 1:
                                        j = i - 1
                                        while self.__contents[j] != ';' and self.__contents[j] != '{':
                                                j -= 1;
                                        node_start_pos = j+1
                        elif self.__contents[i] == '}':
                                node_start -= 1
                                if node_start == 0:
                                        node_end_pos = i+1
                                        subnodes.append((node_start_pos, node_end_pos))
                return subnodes
        def find_sub_nodes(self, deepth = 0):
                """
                """
                if deepth != 0:
                        return
                nodes = []
                for node_pos in self.find_sub_nodes_pos():
                        #print(node_pos)
                        node = Node(self.__contents[node_pos[0]:node_pos[1]], deepth+1)
                        nodes.append(node)
                return nodes
        def dump(self, deepth = 0):
                indent_string = '\t'* deepth
                print(indent_string, self.__name, ' {', sep='')
                for key in self.__attributes:
                        if self.__attributes[key]:
                                print(indent_string, '\t', key, ' = ', self.__attributes[key], ';', sep='')
                        else:
                                print(indent_string, '\t', key, ';', sep='')
                for node in self.__subnodes:
                        print()
                        node.dump(deepth+1)
                print(indent_string, '};', sep='')

def dts_parser(filename):
        with open(filename, 'r') as fd:
                contents = fd.read()
        contents = re.sub(re.compile('/.*/;'), '', contents)
        contents = re.sub(re.compile('\s+'), ' ', contents)
        contents = re.sub(re.compile('/\s\{'), 'root {', contents)

        #pattern = re.compile('\S*\s{([^{}]*({[^{}]*})*[^{}]*)*}')
        pattern = re.compile('\S*\s{.*}')
        node_contents = pattern.search(contents).group(0)
        root = Node(node_contents)
        return root

if __name__ == "__main__":
        parser = ArgumentParser(description = "Parse gpio configuration in dts file")
        parser.add_argument("-f", metavar='dtsfile', nargs=1, type=str, required=True, help = "parse dts file")
        command = parser.parse_args()

        RootNode = dts_parser(command.f[0])
