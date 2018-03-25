#!/usr/bin/env python3
# Written by zhangbo10073794
# parse compiled dts or dtb file, check infomation for bsp
# dtb file is processed by dtc command, Such as ./out/target/product/msm8937_64/obj/KERNEL_OBJ/scripts/dtc/dtc -I dtb -O dts ./out/target/product/msm8937_64/obj/KERNEL_OBJ/arch/arm64/boot/dts/qcom/zte-msm8940-pmi8940-vita.dtb
# Version: 1.0

from argparse import ArgumentParser
import re
import os
import string
import tempfile
import sys
import fnmatch

class Node():
        def __init__(self):
                self.__attributeslist = [] #reg = <0x2>; saved as ['reg', '<0x2>']
                self.__attributesmap = None #reg = <0x2>; saved as {'reg':'<0x2>'}
                self.__name = None
                self.__subnodes = []
        def addstatement(self, statement):
                """
                        statement is stripped and without ';' character
                """
                if statement:
                        try:
                                i = statement.index('=')
                                self.__attributeslist.append([statement[0:i].strip(), statement[i+1:].strip()])
                        except:
                                self.__attributeslist.append([statement.strip(),''])
        @property
        def name(self):
                if not self.__name:
                        raise ValueError('node name is not set yet')
                return self.__name
        @name.setter
        def name(self, value):
                if not isinstance(value, str):
                        raise ValueError('value must be str type')
                self.__name = value
        def addsubnode(self, node):
                if not isinstance(node, Node):
                        raise TypeError('node must be instance of Node')
                self.__subnodes.append(node)
        @property
        def subnodes(self):
                return self.__subnodes
        @property
        def attributes(self):
                if not self.__attributesmap:
                        self.__attributesmap = dict(self.__attributeslist)
                return self.__attributesmap
        def dump(self, deepth = 0):
                if self.isDisabled():
                        return
                indent_string = '\t'* deepth
                print(indent_string, self.name, ' {', sep='')
                for attribute, value in self.__attributeslist:
                        if value:
                                print(indent_string, '\t', attribute, ' = ', value, ';', sep='')
                        else:
                                print(indent_string, '\t', attribute, ';', sep='')
                for node in self.__subnodes:
                        print()
                        node.dump(deepth+1)
                print(indent_string, '};', sep='')
        def isDisabled(self):
                if 'status' in self.attributes.keys() and self.attributes['status'] == '"disabled"':
                        return True
                return False

class DtsInfo():
        def __init__(self, rootnode):
                if not isinstance(rootnode, Node):
                        raise TypeError('rootnode must be instance of Node')
                if rootnode.name != '/':
                        raise ValueError('root node must be /')
                self.__rootnode = rootnode
                #there is pinctrl handle in 8909 8940, and no in sdm670 sdm845
                self.__pinctrl_phandle = self.get_pinctrl_phandle()
                self.__gpio_num_max = None # get gpio num later
        def __find_subnode_by_patternname_recursive(self, node, pattern):
                """
                Return: [node1, node2, ...]
                """
                ret = []
                if re.fullmatch(pattern, node.name):
                        ret.append(node)
                for subnode in node.subnodes:
                        nodes = self.__find_subnode_by_patternname_recursive(subnode, pattern)
                        if nodes:
                                ret.extend(nodes)
                return ret
        def find_node_by_patternname(self, pattern):
                        return self.__find_subnode_by_patternname_recursive(self.__rootnode, pattern)
        def get_pinctrl_phandle(self):
                """
                        phandle = <ox23>; return '0x23'
                        Raise exception ValueError need handler outside
                """
                node = self.find_node_by_patternname(re.compile('pinctrl@[x0-9a-fA-F]+'))
                if not node:
                        #raise ValueError("can't get pinctrl node")
                        return '0xffffffff'
                elif len(node) != 1:
                        raise ValueError('there is more than one pinctrl node')
                node = node.pop()
                phandle = re.search(re.compile('0x[0-9a-fA-F]+'), node.attributes['phandle']).group(0)
                return phandle
        def __find_node_statement_by_statementpattern_recursive(self, node, pattern):
                """
                        Return: {noden: {key1:value1, key2:value2}]
                """
                ret = dict()
                for key in node.attributes.keys():
                        if node.attributes[key]:
                                if re.fullmatch(pattern, key+' = '+node.attributes[key]):
                                        if node in ret.keys():
                                                ret[node].update({key:node.attributes[key]})
                                        else:
                                                ret[node] = {key:node.attributes[key]}
                        else:
                                if re.fullmatch(pattern, key):
                                        if node in ret.keys():
                                                ret[node].update({key:''})
                                        else:
                                                ret[node] = {key:''}
                for subnode in node.subnodes:
                        ret.update(self.__find_node_statement_by_statementpattern_recursive(subnode, pattern))
                return ret
        def find_node_statement_by_statementpattern(self, pattern):
                return self.__find_node_statement_by_statementpattern_recursive(self.__rootnode, pattern)
        def __get_node_attribute_gpio_use_recursive(self, node):
                """
                        Return: [(node, attribute, gpio), ...]
                """
                ret = []
                if node.isDisabled():
                        return ret
                pattern_string = re.compile('<(\s*' + self.__pinctrl_phandle +  ' 0x[0-9a-fA-F]+\s+0x[0-9a-fA-F]+\s*)+>')
                for attri in node.attributes:
                        if re.fullmatch(pattern_string, node.attributes[attri]):
                                gpio_attribute = re.findall(re.compile('0x[0-9a-fA-F]+'), node.attributes[attri])
                                for gpio in [int(gpio_attribute[i], 16) for i in range(1, len(gpio_attribute), 3)]:
                                        ret.append((node, attri, gpio))
                for subnode in node.subnodes:
                        for item in self.__get_node_attribute_gpio_use_recursive(subnode):
                                ret.append(item)
                return ret
        def gpio_nodename_attribute_used(self):
                """
                        {1: [(name1, attribute1), (name2, attribute2)], 2:[ ... ]}
                """
                ret = dict()
                node_attribute_gpio_used = self.__get_node_attribute_gpio_use_recursive(self.__rootnode)
                for node, nodeattri, gpio in node_attribute_gpio_used:
                        if not gpio in ret.keys():
                                ret[gpio] = []
                        ret[gpio].append((node.name, nodeattri))
                return ret
        def __find_node_by_phandle_recursive(self, node, phandle):
                if 'phandle' in node.attributes.keys() and re.search(re.compile('0x[0-9a-fA-F]+'), node.attributes['phandle']).group(0) == phandle:
                                return node
                for subnode in node.subnodes:
                        ret = self.__find_node_by_phandle_recursive(subnode, phandle)
                        if ret:
                                return ret
                return None
        def __node_pinctrlhandle_use_recursive(self, node):
                """
                        get nodename and pinctrl phandle
                                pinctrl-0 = <0xf9>;
                                pinctrl-1 = <0xfa>;
                                pinctrl-2 = <0xfb>;
                                
                                Return: {node:{'0xf9', '0xfa', '0xfb'}}
                """
                if not isinstance(node, Node):
                        raise TypeError('node must be instance of Node')
                ret = dict()
                if node.isDisabled():
                        return ret
                for key in node.attributes:
                        if re.match(re.compile('^pinctrl-[0-9a-fA-F]+'), key):
                                phandles=set(re.findall(re.compile('0x[0-9a-fA-F]+'), node.attributes[key]))
                                if node in ret.keys():
                                                ret[node].update(phandles)
                                else:
                                        ret[node] = phandles
                for subnode in node.subnodes:
                        ret.update(self.__node_pinctrlhandle_use_recursive(subnode))
                return ret
        def __find_statement_by_pattern_recursive(self, node, pattern):
                """
                Return: {(key1, value1), ...}
                """
                ret = set()
                node_statements = self.__find_node_statement_by_statementpattern_recursive(node, pattern)
                for node in node_statements.keys():
                        for key in node_statements[node].keys():
                                ret.add((key, node_statements[node][key]))
                for subnode in node.subnodes:
                        ret.update(self.__find_statement_by_pattern_recursive(subnode, pattern))
                return ret
                
        def gpio_nodename_pinctrlname_used(self):
                """
                {gpio:{(nodename, pinctrlname), (nodename2, pinctrlname2), ... }, ...}
                """
                nodename_pinctrlname_gpio = [] #{('i2c@78b7000', 'i2c_3_active', '10'), ('i2c@78b7000', 'i2c_3_active', '11'), ... ]
                pinctrl_used = self.__node_pinctrlhandle_use_recursive(self.__rootnode)
                for node in pinctrl_used:
                        for handle in pinctrl_used[node]:
                                pinctrl_node = self.__find_node_by_phandle_recursive(self.__rootnode, handle)
                                if not pinctrl_node:
                                        continue
                                #get gpio
                                statements = self.__find_statement_by_pattern_recursive(pinctrl_node, re.compile('pins.*=([\s",]*gpio\d+[\s",]*)+'))
                                for statement in statements:
                                        gpios = re.findall(re.compile('[0-9]+'), statement[1])
                                        for gpio in gpios:
                                                nodename_pinctrlname_gpio.append((node.name, pinctrl_node.name, int(gpio)))
                #set return format
                ret = dict()
                for nodename, pinctrlname, gpio in nodename_pinctrlname_gpio:
                        if gpio not in ret.keys():
                                ret[gpio] = set()
                        ret[gpio].add((nodename, pinctrlname))
                return ret
        def interruptgpio_nodename_used(self):
                """
                Return: {gpio:{nodename1, nodename2, ...}, ...}
                """
                ret = dict()
                interrupts_node = self.find_node_statement_by_statementpattern(re.compile('interrupt-parent = <0x[0-9a-fA-F]+>')).keys()
                for node in interrupts_node:
                        if re.search(re.compile('0x[0-9a-fA-F]+'), node.attributes['interrupt-parent']).group(0) == self.__pinctrl_phandle:
                                if 'interrupts' in node.attributes.keys():
                                        interrupts_attribute = re.findall(re.compile('0x[0-9a-fA-F]+'), node.attributes['interrupts'])
                                        gpios = [int(interrupts_attribute[i], 16) for i in range(0, len(interrupts_attribute), 2)]
                                        for gpio in gpios:
                                                if not gpio in ret.keys():
                                                        ret[gpio] = set()
                                                ret[gpio].add(node.name)
                return ret                
        def dump_gpio_usage(self, gpio = None, out_fd = sys.stdout):
                """
                        GPIO: 125
                        node:
                                         gpio_leds -> qcom,red-led
                        pinctrl:
                                         gpio_leds -> gpio_led_off
                """
                gpioused = self.gpio_nodename_attribute_used()
                pinctrlconfig = self.gpio_nodename_pinctrlname_used()
                interruptgpio_nodename = self.interruptgpio_nodename_used()
                gpio_num_max = max(max(gpioused.keys()), max(pinctrlconfig.keys()), max(interruptgpio_nodename.keys()))
                if gpio:
                        gpiolist = [gpio]
                else:
                        gpiolist = range(0,gpio_num_max+1)
                for gpionum in gpiolist:
                        print('GPIO:', gpionum, file = out_fd)
                        if gpionum in gpioused.keys():
                                print('node:', file = out_fd)
                                for name, attribute in gpioused[gpionum]:
                                        print('\t', name, '->', attribute, file = out_fd)
                        if gpionum in interruptgpio_nodename.keys():
                                print('interrupt', file = out_fd)
                                for name in interruptgpio_nodename[gpionum]:
                                        print('\t', name, '->', 'interrupts', file = out_fd)
                        if gpionum in pinctrlconfig.keys():
                                print('pinctrl:', file = out_fd)
                                for name, pinctrlname in pinctrlconfig[gpionum]:
                                        print('\t', name, '->', pinctrlname, file = out_fd)

def node_parser(fd, node_name = None):
        """
        Parse node infomation, without nodename and starting '{' and with ending '};'

        nodenmae {
        ----------------------------------
                attribute1;
                subnode {
                };
                subnode {
                };
        };
        -----------------------------------

        Return node
        """
        node = Node()
        if node_name:
                node.name = node_name
        line = fd.readline()
        while line:
                if re.fullmatch('\s*\S+\s+{\s*\n', line): #parse sub node
                        #get node name
                        name = re.search(re.compile('\S+'), line).group(0)
                        subnode = node_parser(fd, name)
                        node.addsubnode(subnode)
                elif re.fullmatch('\s*};\s*\n', line): #end sub node:
                        break
                elif re.sub(re.compile('\s*\n'), '', line): # statement
                        statement = re.sub(re.compile('\s*;\s*\n'), '', line)
                        node.addstatement(statement.strip())
                line = fd.readline()
        return node
def dts_parser(filename = None, fd = None):
        if filename:
                fd = open(filename, 'r')
        elif not fd:
                raise ValueError('either filenmae or fd has value')
        line = fd.readline()
        while line:
                if re.fullmatch('\s*\S+\s+{\s*\n', line): #parse / node
                        #get node name
                        name = re.search(re.compile('\S+'), line).group(0)
                        root = node_parser(fd, name)
                        break
                line = fd.readline()
        fd.close()
        return root

def search_dtc_dtbs():
        """
        This script is excuted in android root directory, so check the path is valid
        """
        rootdir_contents=os.listdir()
        dirs_check={'kernel', 'device', 'vendor', 'cts', 'external', 'framworks'}
        if not len(set(rootdir_contents).intersection(dirs_check)) == len(dirs_check):
                print(os.getcwd(), 'is not android root directory')
                print(sys.argv[0], 'must be excuted in android root directory')
                exit()
        if not 'out' in rootdir_contents:
                print('There is no out directory, please compile bootimg first')
                exit()
        product_target = os.listdir('out/target/product/')
        if product_target:
                dtc_command = './out/target/product/' + product_target[0] + '/obj/KERNEL_OBJ/script/dtc/dtc'
                dtb_file_paths = ['./out/target/product/' + product_target[0] + '/obj/KERNEL_OBJ/arch/arm/boot/dts/qcom/', './out/target/product/' + product_target[0] + '/obj/KERNEL_OBJ/arch/arm64/boot/dts/qcom/']
                dtbs = []
                for path in dtb_file_paths:
                        if os.path.isdir(path):
                                for file in os.listdir(path):
                                        if fnmatch.fnmatch(file, '*.dtb'):
                                                dtbs.append(''.join([path,file]))
        return (dtc_command, dtbs)

def dtsinfo_generator(dtc_command_path, dtb_file_path):
        dtc_command_path = os.path.abspath(dtc_command_path)
        dtb_file_path = os.path.abspath(dtb_file_path)
        if not re.fullmatch(re.compile('.*dtc'), dtc_command_path):
                raise ValueError('dtc comamnd path error')
        elif not os.path.isfile(dtc_command_path):
                raise ValueError(dtc_command_path, 'file not exist or not a regular file')
        if not re.fullmatch(re.compile('.*dtb'), dtb_file_path):
                raise ValueError('dtb file path error')
        elif not os.path.isfile(dtb_file_path):
                raise ValueError(command.c[0], 'file not exist or not a regular file')
        global RootNode
        with os.popen(dtc_command_path + ' -I dtb -O dts ' + dtb_file_path + ' 2>/dev/null') as fd:
                tmpfile = tempfile.TemporaryFile(mode='w+')
                tmpfile.write(fd.read())
                tmpfile.seek(0)
                RootNode = dts_parser(fd = tmpfile)
        dtsinfo = DtsInfo(RootNode)

if __name__ == "__main__":
        parser = ArgumentParser(description = "Parse gpio configuration in compiled dtb file")
        parser.add_argument("-f", metavar='compiled dtsfile', nargs=1, type=str, required=False, help = "Set dts file, which is processed by dtc command")
        command = parser.parse_args()
        dtc_command, dtbs = search_dtc_dtbs()
        if not dtbs:
                print('No compiled dtb file found, please compile bootimg first')
                exit()

        global RootNode
        if command.f:
                RootNode = dts_parser(filename = command.f[0])
                dtsinfo = DtsInfo(RootNode)
                dtsinfo.dump_gpio_usage()
                exit
        for dtb_file in dtbs:
                print('parsing ', dtb_file, '......')
                dtsinfo = dtsinfo_generator(dtc_command, dtb_file)
                basename = os.path.basename(dtb_file)
                result_file = re.sub(re.compile('\.dtb'), '_gpio_use.txt', dtb_file)
                with open(result_file, 'w') as fd:
                        dtsinfo.dump_gpio_usage(out_fd = fd)
                print('saved result to ', result_file)
                print()
