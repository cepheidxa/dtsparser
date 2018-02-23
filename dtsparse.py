#!/usr/bin/env python3
# Written by zhangbo10073794
# parse compiled dts or dtb file, check infomation for bsp
# dtb file is processed by dtc command, Such as ./out/target/product/msm8937_64/obj/KERNEL_OBJ/scripts/dtc/dtc -I dtb -O dts ./out/target/product/msm8937_64/obj/KERNEL_OBJ/arch/arm64/boot/dts/qcom/zte-msm8940-pmi8940-vita.dtb

from argparse import ArgumentParser
import re
import os
import string
import tempfile

gpio_num_max = 150

class Node():
    def __init__(self):
        self.__attributeslist = [] #reg = <0x2>; saved as ['reg', '<0x2>']
        self.__attributesmap = {} #reg = <0x2>; saved as {'reg':'<0x2>'}
        self.__name = ''
        self.__subnodes = []
    def addstatement(self, statement):
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
            self.__attributeslist.append([statement[0:i].strip(), statement[i+1:].strip()])
        else:
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
        indent_string = '\t'* deepth
        print(indent_string, self.name, ' {', sep='')
        for item in self.__attributeslist:
            if item[1]:
                print(indent_string, '\t', item[0], ' = ', item[1], ';', sep='')
            else:
                print(indent_string, '\t', item[0], ';', sep='')
        for node in self.__subnodes:
            print()
            node.dump(deepth+1)
        print(indent_string, '};', sep='')

class DtsInfo():
    def __init__(self, rootnode):
        if not isinstance(rootnode, Node):
            raise TypeError('rootnode must be instance of Node')
        if rootnode.name != '/':
            raise ValueError('root node must be /')
        self.__rootnode = rootnode
        self.__pinctrl_phandle = self.get_pinctrl_phandle()
    def __find_subnode_by_patternname_recursive(self, node, pattern):
        for subnode in node.subnodes:
            if re.fullmatch(pattern, subnode.name):
                return subnode
            node = self.__find_subnode_by_patternname_recursive(subnode, pattern)
            if node:
                return node
        return None
    def find_node_by_patternname(self, pattern):
        for subnode in self.__rootnode.subnodes:
            node  = self.__find_subnode_by_patternname_recursive(subnode, pattern)
            if node:
                return node
        return None
    def get_pinctrl_phandle(self):
        """
            phandle = <ox23>; return '0x23'
        """
        node = self.find_node_by_patternname('pinctrl@[x0-9a-fA-F]+')
        if not node:
            raise ValueError("can't get pinctrl node")
        phandle = re.search(re.compile('0x[0-9a-fA-F]+'), node.attributes['phandle']).group(0)
        return phandle
    def __get_node_attribute_gpio_use_recursive(self, node):
        """
            Return: [(nodename, attribute, gpio), ...]
        """
        ret = []
        if 'status' in node.attributes.keys():
            if node.attributes['status'] == 'disabled':
                return ret
        pattern_string = re.compile('<( *' + self.__pinctrl_phandle +  ' 0x[0-9a-fA-F]+ 0x[0-9a-fA-F]+\s*)+>')
        for attri in node.attributes:
            if re.fullmatch(pattern_string, node.attributes[attri]):
                gpio_attribute = re.findall(re.compile('0x[0-9a-fA-F]+'), node.attributes[attri])
                for gpio in [int(gpio_attribute[i], 16) for i in range(1, len(gpio_attribute), 3)]:
                    ret.append((node.name, attri, gpio))
        for subnode in node.subnodes:
            for item in self.__get_node_attribute_gpio_use_recursive(subnode):
                ret.append(item)
        return ret
    def gpio_node_attribute_used(self):
        """
            {1: [(name1, attribute1), (name2, attribute2)], 2:[ ... ]}
        """
        ret = {}
        node_attribute_gpio_used = self.__get_node_attribute_gpio_use_recursive(self.__rootnode)
        for nodename, nodeattri, gpio in node_attribute_gpio_used:
            if gpio not in ret.keys():
                ret[gpio] = []
            ret[gpio].append((nodename, nodeattri))
        return ret
    def __find_node_by_phandle_recursive(self, node, phandle):
        if 'phandle' in node.attributes.keys():
            if re.search(re.compile('0x[0-9a-fA-F]+'), node.attributes['phandle']).group(0) == phandle:
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
                
                Return: {name:{0xf9, 0xfa, 0xfb}}
        """
        if not isinstance(node, Node):
            raise TypeError('node must be instance of Node')
        ret = {}
        if 'status' in node.attributes.keys():
            if node.attributes['status'] == 'disabled':
                return ret
        for key in node.attributes:
            if re.match(re.compile('^pinctrl-[0-9a-fA-F]+'), key):
                phandles=set(re.findall(re.compile('0x[0-9a-fA-F]+'), node.attributes[key]))
                if node.name in ret.keys():
                        ret[node.name].update(phandles)
                else:
                    ret[node.name] = phandles
        for subnode in node.subnodes:
            ret.update(self.__node_pinctrlhandle_use_recursive(subnode))
        return ret
    def __find_statement_by_pattern_recursive(self, node, pattern):
        ret = set()
        for key in node.attributes:
            statement = re.fullmatch(pattern, key+'='+node.attributes[key])
            if statement:
                ret.add(statement.group(0))
        for subnode in node.subnodes:
            ret.update(self.__find_statement_by_pattern_recursive(subnode, pattern))
        return ret
        
    def gpio_node_pinctrlname_used(self):
        """
        {gpio:[(nodename, pinctrlname), (nodename2, pinctrlname2), ... ], ...}
        """
        node_pinctrlname_gpio = [] #{('i2c@78b7000', 'i2c_3_active', '10'), ('i2c@78b7000', 'i2c_3_active', '11'), ... ]
        pinctrl_used = self.__node_pinctrlhandle_use_recursive(self.__rootnode)
        for name in pinctrl_used:
            for handle in pinctrl_used[name]:
                node = self.__find_node_by_phandle_recursive(self.__rootnode, handle)
                #get gpio
                statements = self.__find_statement_by_pattern_recursive(node, re.compile('pins.*=([\s",]*gpio\d+[\s",]*)+'))
                for statement in statements:
                    gpios = re.findall(re.compile('[0-9]+'), statement)
                    for gpio in gpios:
                        node_pinctrlname_gpio.append((name, node.name, int(gpio)))
        #set return format
        ret = {}
        for nodename, pinctrlname, gpio in node_pinctrlname_gpio:
            if gpio in ret.keys():
                ret[gpio].append((nodename, pinctrlname))
            else:
                ret[gpio] = [(nodename, pinctrlname)]
        return ret
    def dump_gpio_usage(self, gpio = None):
        """
            GPIO: 125
            node:
                     gpio_leds -> qcom,red-led
            pinctrl:
                     gpio_leds -> gpio_led_off
        """
        gpioused = self.gpio_node_attribute_used()
        pinctrlconfig = self.gpio_node_pinctrlname_used()
        if gpio:
            gpiolist = [gpio]
        else:
            gpiolist = range(0,gpio_num_max+1)
        for gpionum in gpiolist:
            print('GPIO:', gpionum)
            if gpionum in gpioused.keys():
                print('node:')
                for name, attribute in gpioused[gpionum]:
                    print('\t', name, '->', attribute)

            if gpionum in pinctrlconfig.keys():
                print('pinctrl:')
                for nodename, pinctrlname in pinctrlconfig[gpionum]:
                    print('\t', nodename, '->', pinctrlname)

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

if __name__ == "__main__":
    parser = ArgumentParser(description = "Parse gpio configuration in dts file")
    parser.add_argument("-f", metavar='compiled dtsfile', nargs=1, type=str, required=False, help = "Set dts file, which is processed by dtc command")
    parser.add_argument("-n", metavar='gpio number', nargs=1, type=int, required=False, help = "Check specific gpio")
    parser.add_argument("-b", metavar='compiled dtb file', nargs=1, type=str, required=False, help = "Set compiled dts file")
    parser.add_argument("-c", metavar='dtc command', nargs=1, type=str, required=False, help = "Set dtc command path")
    command = parser.parse_args()

    global RootNode
    if command.f:
        RootNode = dts_parser(filename = command.f[0])
    elif command.b and command.c:
        if not re.fullmatch(re.compile('.*dtc'), command.c[0]):
            raise ValueError('dtc comamnd path error')
        elif not os.path.isfile(command.c[0]):
            raise ValueError(command.c[0], 'file not exist or not a regular file')
        if not re.fullmatch(re.compile('.*dtb'), command.b[0]):
            raise ValueError('dtb file path error')
        elif not os.path.isfile(command.b[0]):
            raise ValueError(command.c[0], 'file not exist or not a regular file')

        with os.popen(os.path.join('./', command.c[0]) + ' -I dtb -O dts ' + os.path.join('./', command.b[0]) + ' 2>/dev/null') as fd:
            tmpfile = tempfile.TemporaryFile(mode='w+')
            tmpfile.write(fd.read())
            tmpfile.seek(0)
            RootNode = dts_parser(fd = tmpfile)
    else:
        parser.print_help()
        exit()

    #RootNode.dump()
    dtsinfo = DtsInfo(RootNode)
    dtsinfo.dump_gpio_usage()
