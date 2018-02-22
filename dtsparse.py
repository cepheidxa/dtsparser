#!/usr/bin/env python3
# Written by zhangbo10073794
# parse compiled dts files, check info for bsp
# dtb file is processed by dtc command, ./out/target/product/msm8937_64/obj/KERNEL_OBJ/scripts/dtc/dtc -I dtb -O dts ./out/target/product/msm8937_64/obj/KERNEL_OBJ/arch/arm64/boot/dts/qcom/zte-msm8940-pmi8940-vita.dtb

from argparse import ArgumentParser
import re
import string

gpio_num_max = 200

class Node():
	def __init__(self):
		self.__attributes = {}
		self.__keys = []
		self.__name = ''
		self.__subnodes = []
	def AddAttribute(self, key, value = ''):
		self.__attributes[key] = value
		self.__keys.append(key)
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
	def SubNodes(self):
		return self.__subnodes
	def attributes(self):
		return self.__attributes
	def dump(self, deepth = 0):
		indent_string = '\t'* deepth
		print(indent_string, self.Name(), ' {', sep='')
		for key in self.__keys:
			if self.__attributes[key]:
				print(indent_string, '\t', key, ' = ', self.__attributes[key], ';', sep='')
			else:
				print(indent_string, '\t', key, ';', sep='')
		for node in self.__subnodes:
			print()
			node.dump(deepth+1)
		print(indent_string, '};', sep='')

		
class DtsInfo():
	def __init__(self, rootnode):
		if not isinstance(rootnode, Node):
			raise TypeError('rootnode must be instance of Node')
		if rootnode.Name() != '/':
			raise ValueError('pinctrl_phandle parameter must be root node')
		self.__rootnode = rootnode
		self.__pinctrl_phandle = self.get_pinctrl_phandle()
	def __find_subnode_by_pattern(self, node, pattern):
		for subnode in node.SubNodes():
			if re.fullmatch(pattern, subnode.Name()):
				return subnode
	def find_node_by_pattern(self, pattern):
		for subnode in self.__rootnode.SubNodes():
			node  = self.__find_subnode_by_pattern(subnode, pattern)
			if node:
				return node
		return None
	def get_pinctrl_phandle(self):
		node = self.find_node_by_pattern('pinctrl@[x0-9a-fA-F]+')
		if not node:
			raise ValueError("can't get pinctrl node")
		phandle = re.search(re.compile('0x[0-9a-fA-F]+'), node.attributes()['phandle']).group(0)
		return phandle
	def __get_node_gpio_use(self, node):
		"""
			Return: {nodename:{1, 2}, name2:{gpio1, gpio2}}
		"""
		ret = {}
		if 'status' in node.attributes().keys():
			if node.attributes()['status'] == 'disabled':
				return ret
		gpio = []
		pattern_string = '<( *' + self.__pinctrl_phandle +  ' 0x[0-9a-fA-F]+ 0x[0-9a-fA-F]+\s*)+>'
		for key in node.attributes():
			if re.fullmatch(re.compile(pattern_string), node.attributes()[key]):
				gpio_attribute = re.findall(re.compile('0x[0-9a-fA-F]+'), node.attributes()[key])
				for v in [int(gpio_attribute[i], 16) for i in range(1, len(gpio_attribute), 3)]:
					gpio.append(v)
		if gpio:
			ret.update({node.Name():set(gpio)})
		for subnode in node.SubNodes():
			ret.update(self.__get_node_gpio_use(subnode))
		return ret
	def node_gpio_use(self):
		"""
			{1: [name1, name2], 2:[name1, name2]}
		"""
		ret = {}
		node_gpio_used = self.__get_node_gpio_use(self.__rootnode)
		for i in range(gpio_num_max+1):
			nodenames = []
			for name in node_gpio_used:
				if i in node_gpio_used[name]:
					nodenames.append(name)
			if nodenames:
				ret[i] = nodenames
		return ret

	def __find_node_by_phandle(self, node, phandle):
		if 'phandle' in node.attributes().keys():
			if node.attributes()['phandle'] == phandle:
				return node
		for subnode in node.SubNodes():
			ret = self.__find_node_by_phandle(subnode, phandle)
			if ret:
				return ret
		return None
	def __node_pinctrl_parser(self, node):
		"""
			get nodename and pinctrl phandle
				pinctrl-0 = <0xf9>;
				pinctrl-1 = <0xfa>;
				pinctrl-2 = <0xfb>;
				
				Return: {name, [0xf9, 0xfa, 0xfb]}
		"""
		ret = {}
		if 'status' in node.attributes().keys():
			if node.attributes()['status'] == 'disabled':
				return ret
		if not isinstance(node, Node):
			raise TypeError('node must be instance of Node')
		for key in node.attributes():
			if re.match(re.compile('^pinctrl-\d'), key):
				handles=re.findall(re.compile('0x[0-9a-fA-F]+'), node.attributes()[key])
				if node.Name() in ret.keys():
					for v in handles:
						ret[node.Name()].append(v)
				else:
					ret[node.Name()] = handles
		for subnode in node.SubNodes():
			ret.update(self.__node_pinctrl_parser(subnode))
		return ret
	def __find_attribute_by_pattern_recursive(self, node, pattern):
		ret = set()
		for key in node.attributes():
			statement = re.fullmatch(pattern, key+'='+node.attributes()[key])
			if statement:
				ret.add(statement.group(0))
		for subnode in node.SubNodes():
			ret.update(self.__find_attribute_by_pattern_recursive(subnode, pattern))
		return ret
		
	def pinctrl_configuration(self):
		"""
		{gpio:(nodename, pinctrlname)}
		"""
		pinctrlgpiomap = {} #{'i2c@78b7000': [('i2c_3_active', '10'), ('i2c_3_active', '11'), ('i2c_3_sleep', '10'), ('i2c_3_sleep', '11')],....
		pinctrl_used = self.__node_pinctrl_parser(self.__rootnode)
		for name in pinctrl_used:
			for handle in pinctrl_used[name]:
				node = self.__find_node_by_phandle(self.__rootnode, '<'+handle+'>')
				#get gpio
				statements = self.__find_attribute_by_pattern_recursive(node, re.compile('pins.*=([\s",]*gpio\d+[\s",]*)+'))
				for statement in statements:
					gpios = re.findall(re.compile('[0-9a-fA-F]+'), statement)
					if not name in pinctrlgpiomap.keys():
						pinctrlgpiomap[name] = []
					for gpio in gpios:
						pinctrlgpiomap[name].append((node.Name(), gpio))
		#set return format
		ret = {}
		for i in range(gpio_num_max+1):
			for nodename in pinctrlgpiomap:
				for item in pinctrlgpiomap[nodename]:
					if int(item[1], 10) == i:
						if not i in ret.keys():
							ret[i] = []
						ret[i].append((nodename, item[0]))
		return ret

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
	node = Node()
	if node_name:
		node.SetName(node_name)
	length = len(contents)
	prepos = pos = start_pos + 1  # contents[prepos:pos] is used to check an attribute statement
	i = start_pos + 1
	while i < length:
		if contents[i] == '{': #a node start position
			#get node name
			j = i -1
			while j >= 0 and contents[j] not in [';', '{']:
				j -= 1
			name = contents[j:i].translate(str.maketrans('', '', ';{')).strip()
			subnode, pos = node_parser(contents, i, name)
			node.AddSubNode(subnode)
			i = pos
			prepos = i + 1
		elif contents[i] == '}':
			prepos = i + 1
			break
		elif contents[i] == ';':
			pos = i
			node.AddStatement(contents[prepos:pos].strip())
			prepos = i + 1
		i += 1
	while contents[i] != ';':
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
	#RootNode.dump()

	dtsinfo = DtsInfo(RootNode)
	gpioused_by_node = dtsinfo.node_gpio_use()
	pinctrlconfig = dtsinfo.pinctrl_configuration()
	for gpio in range(gpio_num_max+1):
		print('GPIO:', gpio)
		if gpio in gpioused_by_node.keys():
			print('node:')
			for name in gpioused_by_node[gpio]:
				print('\t', name)

		if gpio in pinctrlconfig:
			print('pinctrl:')
			for item in pinctrlconfig[gpio]:
				print('\t', item[0], item[1])