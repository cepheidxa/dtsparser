#!/usr/bin/env python3
# Written by zhangbo10073794
# parse compiled dts or dtb file, check infomation for bsp
# dtb file is processed by dtc command, Such as
#    ./out/target/product/msm8937_64/obj/KERNEL_OBJ/scripts/dtc/dtc -I dtb -O dts
#    ./out/target/product/msm8937_64/obj/KERNEL_OBJ/arch/arm64/boot/dts/qcom/zte-msm8940-pmi8940-vita.dtb
#

from argparse import ArgumentParser
import re
import os
import tempfile
import sys
import enum

__version__ = "1.1.1"

class Platform(enum.Enum):
    QUALCOMM = 1
    MTK = 2
    SPRD = 3


class Node():
    def __init__(self):
        self.__propslist = []  # reg = <0x2>; saved as ['reg', '<0x2>']
        self.__propsmap = None  # reg = <0x2>; saved as {'reg': '<0x2>'}
        self.__name = None
        self.__subnodes = []
        self.__parent = None
        self.__propschanged = 1

    def addstatement(self, statement):
        """
            property and value is stripped, property and value doesn't reserve end ';' character,
        """
        statement = re.sub(re.compile('\s*;\s*\n*$'), '', statement)
        if statement:
            try:
                i = statement.index('=')
                self.__propslist.append([statement[0:i].strip(), statement[i+1:].strip()])
            except:
                self.__propslist.append([statement.strip(), ''])
        self.__propschanged = 1

    @property
    def name(self):
        if not self.__name:
            raise ValueError('node name is not set yet')
        return self.__name

    @name.setter
    def name(self, value):
        """
            value must be str, must be set and only set once
        """
        if not isinstance(value, str):
            raise ValueError('value must be str type')
        if self.__name:
            raise ValueError('Node name has been set')
        self.__name = value

    @property
    def parent(self):
        return self.__parent

    @parent.setter
    def parent(self, node):
        if not isinstance(node, Node):
            raise ValueError('node must be instance of Node')
        if self.__parent:
            raise ValueError('node parent has been set')
        if node == self:
            raise ValueError('node parent is set to itself, set parent to None if it has no parent')
        self.__parent = node

    def addsubnode(self, node):
        if not isinstance(node, Node):
            raise ValueError('node must be instance of Node')
        node.parent = self
        self.__subnodes.append(node)

    @property
    def subnodes(self):
        return self.__subnodes

    @property
    def props(self):
        if self.__propschanged:
            self.__propsmap = dict(self.__propslist)
            self.__propschanged = 0
        return self.__propsmap

    def dump(self, deepth=0, withdisabled = False):
        """
            dump disabled node if withdisabled = True, else doesn't dump disabled node
        """
        if not self.__name:
            raise ValueError('Node name is not set')
        result = []
        if not withdisabled and self.isDisabled():
            return ''.join(result)
        indent_string = '\t' * deepth
        result.append(''.join([indent_string, self.name, ' {\n']))
        for prop, value in self.__propslist:
            if value:
                result.append(''.join([indent_string, '\t', prop, ' = ', value, ';\n']))
            else:
                result.append(''.join([indent_string, '\t', prop, ';\n']))
        for node in self.__subnodes:
            result.append('\n')
            result.append(node.dump(deepth + 1, withdisabled=withdisabled))
        result.append(''.join([indent_string, '};\n']))
        return ''.join(result)

    def isDisabled(self):
        if 'status' in self.props.keys() and self.props['status'] == '"disabled"':
            return True
        return False


class Dts():
    def __init__(self, filename, with_disabled_node=False):
        self.__with_disabled_node = with_disabled_node
        self.__rootnode = self.__dts_parser(filename)
        self.__platform = self.get_platform()

    def dump(self):
        return self.__rootnode.dump(withdisabled=True)

    def find_node_by_patternname(self, pattern):
        """
            return list of subnode which name fully matches pattern
        """
        return self.find_subnode_by_patternname_recursive(self.__rootnode, pattern)

    def get_platform(self):
        compatible_value = self.__rootnode.props['compatible']
        if re.search(re.compile('(sprd)|(Spreadtrum)', re.IGNORECASE), compatible_value):
            return Platform.SPRD
        elif re.search(re.compile('(mediatek)|(mtk)',re.IGNORECASE), compatible_value):
            return Platform.MTK
        elif re.search(re.compile('qcom', re.IGNORECASE), compatible_value):
            return Platform.QUALCOMM

    def find_node_by_phandle(self, phandle):
        node_statement = self.find_node_statement_by_statementpattern('phandle = <{}>'.format(phandle))
        if node_statement:
            return list(node_statement.keys())[0]
        else:
            print('node with phandle = <{}> is not found, please check'.format(phandle))
            return None

    def find_node_ancestor_with_compatible_prop(self, node):
        """
            reurn node or its ancestor node which with compatible property
        """
        if not isinstance(node, Node):
            raise ValueError('node must be a Node')
        if 'compatible' in node.props.keys():
            return node
        ret = node.parent
        while ret:
            if 'compatible' in ret.props.keys():
                return ret
            ret = ret.parent
        return ret

    def find_node_statement_by_statementpattern(self, pattern):
        """
            Return: {node: {prop1:value1, prop2:value2}, ....]
            statement is prop = "value" or prop;
        """
        return self.find_node_statement_by_statementpattern_recursive(self.__rootnode, pattern)

    def get_interrup_controller_node_phandle(self):
        """
            reurn {node0: phandle1, node1: phandle1}
            phandle has no '<' or '>' character, its value as 0x23
        """
        ret = dict()
        nodes_statement = self.find_node_statement_by_statementpattern('interrupt-controller')
        for node in nodes_statement:
            if 'phandle' in node.props:
                phandle = node.props['phandle']
                phandle = phandle[phandle.index('<')+1:phandle.index('>')]
                ret[node] = phandle
        return ret

    def get_gpiocontroller_node_phandle(self):
        """
            reurn {node0: phandle1, node1: phandle1}
            phandle has no '<' or '>' character, its value as 0x23
        """
        ret = dict()
        nodes_statement = self.find_node_statement_by_statementpattern('gpio-controller')
        for node in nodes_statement:
            if 'phandle' in node.props:
                phandle = node.props['phandle']
                phandle = phandle[phandle.index('<')+1:phandle.index('>')]
                ret[node] = phandle
        return ret

    def get_pinctrlnode(self):
        usedpinctrlhandle_nodeinfo = self.get_used_pinctrl_phandle_node()
        pinctrlnodes = []
        for handle in usedpinctrlhandle_nodeinfo:
            node = self.find_node_by_phandle(handle)
            if not node:
                continue
            node = self.find_node_ancestor_with_compatible_prop(node)
            if not node in pinctrlnodes:
                pinctrlnodes.append(node)
        return pinctrlnodes

    def get_used_pinctrl_phandle_node(self):
        """
            return {phandle: [node1, node2], ....}
            pinctrl-0 = <0x618 0x619>', phanle: 0x618 and 0x619
            Raise exception ValueError need handler outside
        """
        ret = dict()
        nodes_statement = self.find_node_statement_by_statementpattern(re.compile('pinctrl-[0-9]+ = <( *0x[0-9a-fA-F]+ *)+>'))
        for node in nodes_statement:
            for prop in nodes_statement[node]:
                for phandle in re.split(re.compile('[<> ]'), nodes_statement[node][prop]):
                    if phandle:
                        if not phandle in ret.keys():
                            ret[phandle] = []
                        ret[phandle].append(node)
        return ret

    def get_pinctrl_gpio_node_info(self, pinctrlnode):
        """
            return dict  {gpio1: [node1.name->pinctrlnodename, ...], gpio2: [node2.name->pinctrlnodename ...], ...}
        """
        if not isinstance(pinctrlnode, Node):
            raise ValueError('pinctrlnode must be a node')
        ret = dict()
        phandles_node = self.get_used_pinctrl_phandle_node()
        for phandle in phandles_node:
            node = self.find_node_by_phandle(phandle)
            if not node:
                continue
            node = self.find_node_ancestor_with_compatible_prop(node)
            if node != pinctrlnode:
                continue
            for node_use_pinctrl in phandles_node[phandle]:
                subpinctrlnode = self.find_node_by_phandle(phandle)
                if not subpinctrlnode:
                    continue
                if self.__platform == Platform.QUALCOMM:
                    node_statement = self.find_node_statement_by_statementpattern_recursive(subpinctrlnode, 'pins = .*gpio[0-9].*')
                    for node in node_statement.keys():
                        pins = node_statement[node]
                        for prop in pins.keys():
                            value = pins[prop]
                            gpio_property = re.findall(re.compile('[0-9]+'), value)
                            for value in gpio_property:                        
                                num = int(value)
                                if not num in ret.keys():
                                    ret[num] = []
                                ret[num].append((node_use_pinctrl, subpinctrlnode))
                elif self.__platform == Platform.MTK:
                    node_statement = self.find_node_statement_by_statementpattern_recursive(subpinctrlnode, 'pins\s+=\s+<\s*0x[0-9a-fA-F]+\s*>')
                    for node in node_statement.keys():
                        pins = node_statement[node]
                        for prop in pins.keys():
                            value = pins[prop]
                            value = int(value[value.index('<')+1:value.index('>')], 16)
                            num = (value & 0xFF00) >> 8
                            if not num in ret.keys():
                                ret[num] = []
                            ret[num].append((node_use_pinctrl, subpinctrlnode))
                elif self.__platform == Platform.SPRD:
                    node_statement = self.find_node_statement_by_statementpattern_recursive(subpinctrlnode, 'pins = <(\s*0x[0-9a-fA-F]+\s*)+>')
                    for node in node_statement.keys():
                        pins = node_statement[node]
                        for prop in pins.keys():
                            value = pins[prop]
                            gpio_property = re.findall(re.compile('0x[0-9a-fA-F]+'), value)
                            for value in [int(gpio_property[i], 16) for i in range(0, len(gpio_property), 2)]:
                                num = (value >>20) & 0xFFF
                                if not num in ret.keys():
                                    ret[num] = []
                                ret[num].append((node_use_pinctrl, subpinctrlnode))
        return ret       

    def gpio_nodename_property_used(self, gpiocontroller_node):
        """
            Return all gpio used of node and its subnode, {gpio1: [(node1, property1), (node2, property2)], gpio2:[ ... ]}
        """
        ret = dict()
        node_property_gpio_used = self.get_node_property_gpio_use_recursive(self.__rootnode, gpiocontroller_node)
        for node, prop, gpio in node_property_gpio_used:
            if not gpio in ret.keys():
                ret[gpio] = []
            ret[gpio].append((node, prop))
        return ret

    def interruptgpio_nodename_used(self, interruptcontroller_node):
        """
        Return: {gpio:{nodename1, nodename2, ...}, ...}
        """
        ret = dict()
        interruptcontroller_phandle = re.search(re.compile('0x[0-9a-fA-F]+'), interruptcontroller_node.props['phandle']).group(0)
        interrupts_node = self.find_node_statement_by_statementpattern(re.compile('interrupt-parent = <0x[0-9a-fA-F]+>')).keys()
        for node in interrupts_node:
            if re.search(re.compile('0x[0-9a-fA-F]+'), node.props['interrupt-parent']).group(0) == interruptcontroller_phandle:
                if 'interrupts' in node.props.keys():
                    interrupts_property = re.findall(re.compile('0x[0-9a-fA-F]+'), node.props['interrupts'])
                    gpios = [int(interrupts_property[i], 16) for i in range(0, len(interrupts_property), 2)]
                    for gpio in gpios:
                        if not gpio in ret.keys():
                            ret[gpio] = set()
                        ret[gpio].add(node.name)
        return ret

    def dump_gpio_interrupt_pinctrl_usage(self):
        interrupt_nodes_phandle = self.get_interrup_controller_node_phandle()
        gpiocontroller_nodes_phandle = self.get_gpiocontroller_node_phandle()
        pinctrlnodes = self.get_pinctrlnode()

        nodes = set()
        for node in interrupt_nodes_phandle:
            nodes.add(node)
        for node in gpiocontroller_nodes_phandle:
            nodes.add(node)
        for node in pinctrlnodes:
                nodes.add(node)
        first = True
        msg_list = []
        for node in nodes:
            if 'compatible' in node.props.keys():
                if node in gpiocontroller_nodes_phandle:
                    gpio_nodeinfo = self.gpio_nodename_property_used(node)
                else:
                    gpio_nodeinfo = dict()
                if node in gpiocontroller_nodes_phandle:
                    interrupt_nodeinfo = self.interruptgpio_nodename_used(node)
                else:
                    interrupt_nodeinfo = dict()
                if node in pinctrlnodes:
                    pictrl_nodeinfo = self.get_pinctrl_gpio_node_info(node)
                else:
                    pictrl_nodeinfo = dict()

                nums = list(gpio_nodeinfo.keys()) + list(interrupt_nodeinfo.keys()) + list(pictrl_nodeinfo.keys())
                nums = list(set(nums))
                nums.sort()
                if not nums:
                    continue
                if not first:
                    msg_list.append('-------------------------------------------------------------------------\n')
                else:
                    first = False
                msg_list.append('{} {{\n\t\'compatible\' = {};\n}}\n'.format(node.name, node.props['compatible']))
                for num in nums:
                    msg_list.append('{}:\n'.format(num))
                    try:
                        if gpio_nodeinfo[num]:
                            usage = set()
                            for node, prop in gpio_nodeinfo[num]:
                                usage.add('\t{} -> {}\n'.format(node.name, prop))
                            if usage:
                                msg_list.append('node:\n')
                            msg_list += list(usage)
                    except KeyError:
                        pass
                    try:
                        if interrupt_nodeinfo[num]:
                            usage = set()
                            for nodename in interrupt_nodeinfo[num]:
                                usage.add('\t{}\n'.format(nodename))
                            if usage:
                                msg_list.append('interrupt:\n')
                            msg_list += list(usage)
                    except KeyError:
                        pass
                    try:
                        if pictrl_nodeinfo[num]:
                            usage = set()
                            for node1, node2 in pictrl_nodeinfo[num]:
                                usage.add('\t{} -> {}\n'.format(node1.name, node2.name))
                            if usage:
                                msg_list.append('pinctrl:\n')
                            msg_list += list(usage)
                    except KeyError:
                        pass
        return ''.join(msg_list)

    def find_node_by_phandle_recursive(self, node, phandle):
        """
            return sunode or node which phandle is <phandle>, phandle must be a str
            phandle = 0xb
            node {
                phandle = <0xb>;
            }
        """
        if not isinstance(phandle, str):
            raise ValueError('phandle must be a str')
        if not isinstance(node, Node):
            raise ValueError('phandle must be a Node')

        if 'phandle' in node.props.keys() \
            and re.search(re.compile('0x[0-9a-fA-F]+'), node.props['phandle']).group(0) == phandle:
                return node
        for subnode in node.subnodes:
            ret = self.find_node_by_phandle_recursive(subnode, phandle)
            if ret:
                return ret
        return None

    def find_subnode_by_patternname_recursive(self, node, pattern):
        """
        Return: [node1, node2, ...]
        """
        if not isinstance(node, Node):
            raise ValueError('phandle must be a Node')

        ret = []
        if re.fullmatch(pattern, node.name):
            ret.append(node)
        for subnode in node.subnodes:
            nodes = self.find_subnode_by_patternname_recursive(subnode, pattern)
            if nodes:
                ret.extend(nodes)
        return ret

    def find_node_statement_by_statementpattern_recursive(self, node, pattern):
        """
            Return: {node1: {key1:value1, key2:value2}]
        """
        if not isinstance(node, Node):
            raise ValueError('node must be a Node')
        ret = dict()

        for prop in node.props.keys():
            if node.props[prop]:
                if re.fullmatch(pattern, prop + ' = ' + node.props[prop]):
                    if node in ret.keys():
                        ret[node].update({prop: node.props[prop]})
                    else:
                        ret[node] = {prop: node.props[prop]}
            else:
                if re.fullmatch(pattern, prop):
                    if node in ret.keys():
                        ret[node].update({prop: ''})
                    else:
                        ret[node] = {prop: ''}
        for subnode in node.subnodes:
            ret.update(self.find_node_statement_by_statementpattern_recursive(subnode, pattern))
        return ret

    def get_node_property_gpio_use_recursive(self, node, gpiocontroller_node):
        """
            Return all gpio used of node and its subnode, [(node1, property, gpio), ...]
        """
        ret = []
        if 'phandle' in gpiocontroller_node.props.keys():
            phandle = re.search(re.compile('0x[0-9a-fA-F]+'), gpiocontroller_node.props['phandle']).group(0)
            if not phandle:
                return ret
            pattern_string = re.compile('<(\s*' + phandle + '\s+0x[0-9a-fA-F]+\s+0x[0-9a-fA-F]+\s*)+>')
            for prop in node.props:
                if re.fullmatch(pattern_string, node.props[prop]):
                    gpio_property = re.findall(re.compile('0x[0-9a-fA-F]+'), node.props[prop])
                    for gpio in [int(gpio_property[i], 16) for i in range(1, len(gpio_property), 3)]:
                        ret.append((node, prop, gpio))
            for subnode in node.subnodes:
                for item in self.get_node_property_gpio_use_recursive(subnode, gpiocontroller_node):
                    ret.append(item)
        else:
            raise ValueError('there is no phandle prop in gpiocontroller_node {}'.format(gpiocontroller_node.name))

        return ret

    def __node_parser(self, fd, node_name=None):
        """
        Parse node infomation, without nodename and starting '{' but with ending '};'

        nodenmae {
        ----------------------------------
            prop1;
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
            if re.fullmatch('\s*\S+\s+{\s*\n', line):  # parse sub node
                #get node name
                name = re.search(re.compile('\S+'), line).group(0)
                subnode = self.__node_parser(fd, name)
                if self.__with_disabled_node:
                    node.addsubnode(subnode)
                elif not subnode.isDisabled():
                    node.addsubnode(subnode)
            elif re.fullmatch('\s*};\s*\n', line):  # end sub node:
                break
            elif re.sub(re.compile('\s*\n'), '', line):  # statement
                statement = re.sub(re.compile('\s*;\s*\n'), '', line)
                node.addstatement(statement.strip())
            line = fd.readline()
        return node

    def __dts_parser(self, filename):
        with open(filename, 'r') as fd:
            line = fd.readline()
            while line:
                if re.fullmatch('\s*\S+\s+{\s*\n', line):  # parse / node
                    #get node name
                    name = re.search(re.compile('\S+'), line).group(0)
                    root = self.__node_parser(fd, name)
                    break
                line = fd.readline()
        return root


def search_dtc_dtbs():
    """
    This script is excuted in android root directory, so check the path is valid
    """
    rootdir_contents = os.listdir()
    dirs_check = {'kernel', 'device', 'vendor', 'cts', 'external', 'frameworks'}
    if not len(set(rootdir_contents).intersection(dirs_check)) == len(dirs_check):
        errmsg = 'Error: {0} is not android root directory, {1} must be excuted in android root directory'.format(os.getcwd(), sys.argv[0])
        print(errmsg)
        exit()
    if not 'out' in rootdir_contents:
        errmsg = 'There is no out directory, please compile bootimg first'
        print(errmsg)
        exit()
    print('searching dtc command and dtb files, please wait......')
    with os.popen('find ./out/ -name dtc -type f 2>/dev/null') as fd:
        dtc_find_list = fd.read()
    dtc_find_list = dtc_find_list.split()
    with os.popen('find ./out/target/product/ -name *.dtb -type f 2>/dev/null') as fd:
        dtb_find_list = fd.read()
    dtb_find_list = dtb_find_list.split()
    for dtc_file in dtc_find_list:
        dtc_command = re.search(re.compile('.*out/.*/dtc'), dtc_file)
        if dtc_command:
            dtc_command = dtc_command.group(0)
            with os.popen( dtc_command + ' -h ' + '2>/dev/null') as fd:
                help_msg = fd.read()
            if re.search(re.compile('(device tree blob)|(device tree source text)'), help_msg):
                break
    if not dtc_command:
        raise ValueError('no dtc command found')
    dtbs = []
    for dtb_file in dtb_find_list:
        dtb = re.search(re.compile('.*out/target/product/.*arch/arm.*dtb'), dtb_file)
        if dtb:
            dtbs.append(dtb.group(0))
    if not dtbs:
        raise ValueError('no dtb file found')

    return (dtc_command, dtbs)


if __name__ == "__main__":
    parser = ArgumentParser(description="Parse gpio configuration in compiled dtb file")
    parser.add_argument("-f", metavar='compiled_dtsfile', nargs=1, type=str, required=False, help="Set dts file, which is processed by dtc command")
    command = parser.parse_args()

    if command.f:
        dts = Dts(command.f[0])
        msg = dts.dump_gpio_interrupt_pinctrl_usage()
        print(msg)
        exit()

    dtc_command, dtbs = search_dtc_dtbs()
    for dtb_file in dtbs:
        print('parsing {0} ......'.format(dtb_file))
        with os.popen(dtc_command + ' -I dtb -O dts ' + dtb_file + ' 2>/dev/null') as fd:
            dtsfile = tempfile.mkstemp(suffix='dtstmpfile')
            with open(dtsfile[1], 'w') as tfd:
                tfd.write(fd.read())
        dts = Dts(dtsfile[1])
        os.unlink(dtsfile[1])
        result_file = re.sub(re.compile('\.dtb'), '_gpio_use.txt', dtb_file)
        with open(result_file, 'w') as fd:
            fd.write(dts.dump_gpio_interrupt_pinctrl_usage())
        print('saved result to ', result_file)
        print()     
