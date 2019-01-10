#!/usr/bin/env python3

import unittest
import fnmatch
import os
import dtsparser
import re
import cProfile


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

    def test_parent(self):
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
        self.assertEqual(node31.parent, node3)
        self.assertEqual(node21.parent, node2)
        self.assertEqual(node111.parent, node11)
        self.assertEqual(node12.parent, node1)
        self.assertEqual(node11.parent, node1)
        self.assertEqual(node1.parent, root)
        self.assertEqual(node2.parent, root)
        self.assertEqual(node3.parent, root)
        self.assertEqual(root.parent, None)

        with self.assertRaises(ValueError):
            node1.parent = root
        node = dtsparser.Node()
        with self.assertRaises(ValueError):
            node.parent = node
        with self.assertRaises(ValueError):
            node.parent = 'sdfskdfj'
        node.parent = root
        with self.assertRaises(ValueError):
            node.parent = root

    def test_addstatement(self):
        node = dtsparser.Node()
        node.addstatement('compatible = "shared-dma-pool";')
        self.assertEqual(len(node.props), 1)
        node.addstatement('reusable;')
        self.assertEqual(len(node.props), 2)
        node.addstatement('alignment = <0x0 0x400000>;')
        self.assertEqual(len(node.props), 3)
        node.addstatement('linux,phandle = <0x100>;')
        self.assertEqual(len(node.props), 4)
        node.addstatement('reg = <0x0 0x90000000 0x0 0x1400000>;')
        self.assertEqual(len(node.props), 5)
        self.assertEqual(node.props['compatible'], '"shared-dma-pool"')
        self.assertEqual(node.props['reusable'], '')
        self.assertEqual(node.props['alignment'], '<0x0 0x400000>')
        self.assertEqual(node.props['linux,phandle'], '<0x100>')
        self.assertEqual(node.props['reg'], '<0x0 0x90000000 0x0 0x1400000>')
        self.assertEqual(len(node.props), 5)
        node.addstatement('compatible = "shared-dma-pool2"')
        self.assertEqual(node.props['compatible'], '"shared-dma-pool2"')
        node.addstatement('compatible = "shared-dma-pool3";\n')
        self.assertEqual(node.props['compatible'], '"shared-dma-pool3"')
        node.addstatement('reusable2')
        self.assertEqual(node.props['reusable2'], '')
        node.addstatement('reusable3;\n')
        self.assertEqual(node.props['reusable3'], '')
        with self.assertRaises(KeyError):
            self.assertEqual(node.props['reusableaaa'], '')

    def test_isDisabled(self):
        node = dtsparser.Node()
        node.addstatement('compatible = "shared-dma-pool";')
        node.addstatement('reusable;')
        node.addstatement('alignment = <0x0 0x400000>;')
        node.addstatement('linux,phandle = <0x100>;')
        node.addstatement('reg = <0x0 0x90000000 0x0 0x1400000>;')
        self.assertFalse(node.isDisabled())
        node.addstatement('status = "ok";')
        self.assertEqual(node.props['status'], '"ok"')
        self.assertFalse(node.isDisabled())
        node.addstatement('status = "okay";')
        self.assertEqual(node.props['status'], '"okay"')
        self.assertFalse(node.isDisabled())
        node.addstatement('status = "disabled";')
        self.assertEqual(node.props['status'], '"disabled"')
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
        with self.assertRaises(ValueError):
            root.addsubnode('aaa')
        with self.assertRaises(ValueError):
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


class DtsTest(unittest.TestCase):
    def setUp(self):
        self.__qualcomm_dts_file = 'sm8150-dtb-sm8150-sdx50m-mtp-overlay.dts'
        self.__mtk_dts_file = 'mt6771-dtb-k71v1_64_bsp.dts'
        self.__sprd_dts_file = 'sp9863a-1h10-native-dtb-sp9863a-1h10-overlay.dts'

    def test_dump(self):
        self.__dtsfiles = []
        for file in os.listdir('.'):
            if fnmatch.fnmatch(file, '*.dts'):
                self.__dtsfiles.append(file)
        for file in self.__dtsfiles:
            dts = dtsparser.Dts(file, with_disabled_node=True)
            with open(file, 'r') as fd:
                filecontents = fd.read()
            filecontents_header =  filecontents[:re.search(re.compile('/ {'), filecontents).span()[0]]
            self.assertEqual(filecontents, filecontents_header+dts.dump())

    def test_get_platform(self):
        dts = dtsparser.Dts(self.__qualcomm_dts_file)
        self.assertEqual(dts.get_platform(), dtsparser.Platform.QUALCOMM)
        dts = dtsparser.Dts(self.__mtk_dts_file)
        self.assertEqual(dts.get_platform(), dtsparser.Platform.MTK)
        dts = dtsparser.Dts(self.__sprd_dts_file)
        self.assertEqual(dts.get_platform(), dtsparser.Platform.SPRD)

    def test_find_node_by_patternname(self):
        dts = dtsparser.Dts('sm8150-dtb-sm8150-sdx50m-mtp-overlay.dts')
        nodes = dts.find_node_by_patternname('au.*')
        nodenames = [node.name for node in nodes]
        names = ['audio_etm0', 'audio_ext_clk', 'audio_ext_clk_lnbb']
        self.assertTrue(isinstance(nodes, list))
        self.assertEqual(len(nodenames), len(names))
        for name in names:
            self.assertTrue(name in nodenames)
        self.assertGreater(len(dts.find_node_by_patternname('.*au.*')), len(nodenames))

        nodes = dts.find_node_by_patternname('.*gpio.*')
        nodenames = [node.name for node in nodes]
        names = ['module_poweroff_gpio_default', 'cpe_poweroff_gpio_default', 'display-gpio-regulator@0', 'gpio-regulator@1',\
                 'cam-gpio-regulator@2', 'cam-gpio-regulator@3', 'cam-gpio-regulator@4', 'gpio_keys']
        self.assertTrue(isinstance(nodes, list))
        self.assertEqual(len(nodenames), len(names))
        for name in names:
            self.assertTrue(name in nodenames)
        self.assertLess(len(dts.find_node_by_patternname('gpio.*')), len(nodenames))

        nodes = dts.find_node_by_patternname('.*ed')
        nodenames = [node.name for node in nodes]
        names = ['iova-mem-region-shared', 'iova-mem-region-shared', 'red']
        self.assertTrue(isinstance(nodes, list))
        self.assertEqual(len(nodenames), len(names))
        for name in names:
            self.assertTrue(name in nodenames)
        self.assertGreater(len(dts.find_node_by_patternname('.*ed.*')), len(nodenames))

        nodes = dts.find_node_by_patternname('sdjfksfjsoidnvb')
        self.assertTrue(isinstance(nodes, list))
        self.assertEqual(nodes, [])

    def test_find_node_by_phandle(self):
        dts = dtsparser.Dts('sm8150-dtb-sm8150-sdx50m-mtp-overlay.dts')
        node = dts.find_node_by_phandle('0x45')
        self.assertEqual(node.name, 'llcc-bw-opp-table')
        node = dts.find_node_by_phandle('0x84')
        self.assertEqual(node.name, 'qcom,gdsc@0xab00814')
        node = dts.find_node_by_phandle('0x943')
        self.assertEqual(node, None)

    def test_find_node_ancestor_with_compatible_prop(self):
        dts = dtsparser.Dts('sm8150-dtb-sm8150-sdx50m-mtp-overlay.dts')
        nodename = ['qcom,gpu-pwrlevel@0', 'vol_up', 'qcom,gpu-mempool@2']
        nodename_ancestor_with_compatible = ['qcom,gpu-pwrlevels', 'gpio_keys', 'qcom,gpu-mempools' ]
        for i in range(len(nodename)):
            node = dts.find_node_by_patternname(nodename[i])[0]
            node_ancestor_with_compatible = dts.find_node_ancestor_with_compatible_prop(node)
            self.assertEqual(node_ancestor_with_compatible.name, nodename_ancestor_with_compatible[i])

    def test_find_node_statement_by_statementpattern(self):
        dts = dtsparser.Dts('sm8150-dtb-sm8150-sdx50m-mtp-overlay.dts')
        node_statements = dts.find_node_statement_by_statementpattern('phandle = <0x8[01].*')
        self.assertTrue(isinstance(node_statements, dict))
        names = ['pil_npu_region@8bd80000', 'cdsp_regions@98900000']
        self.assertEqual(len(node_statements), len(names))
        for node in node_statements.keys():
            self.assertTrue(node.name in names)
            self.assertFalse(node.isDisabled())
            if node.name == 'pil_npu_region@8bd80000':
                self.assertEqual(node_statements[node], {'phandle': '<0x80>'})
            elif node.name == 'cdsp_regions@98900000':
                self.assertEqual(node_statements[node], {'phandle': '<0x81>'})

        node_statements = dts.find_node_statement_by_statementpattern('qcom,step-charging-enable')
        self.assertTrue(isinstance(node_statements, dict))
        names = ['qcom,qpnp-smb5']
        self.assertEqual(len(node_statements), len(names))
        for node in node_statements.keys():
            self.assertTrue(node.name in names)
            self.assertFalse(node.isDisabled())
            self.assertEqual(node.name, 'qcom,qpnp-smb5')
            self.assertEqual(node_statements[node], {'qcom,step-charging-enable': ''})

        node_statements = dts.find_node_statement_by_statementpattern('sjdkfsonnksdfkiions')
        self.assertTrue(isinstance(node_statements, dict))
        self.assertFalse(node_statements)

    def test_get_interrup_controller_node_phandle(self):
        qualcomm_nodenames = ['qcom,mdss_mdp@ae00000', 'interrupt-controller@17a00000', 'interrupt-controller@0xb220000',
                     'qcom,spmi@c440000', 'qcom,qsee_irq', 'pinctrl@03000000', 'slave-kernel', 'qcom,smp2p-ipa-1-in',
                     'qcom,smp2p-wlan-1-in', 'slave-kernel', 'qcom,smp2p-rdbg2-in', 'slave-kernel',
                     'qcom,sleepstate-in', 'slave-kernel', 'qcom,smp2p-rdbg5-in', 'qcom,smb1390@10', 'qcom,smb1355@c',
                     'aqt1000-i2c-codec@d', 'wcd9xxx-irq']
        mtk_nodenames = ['interrupt-controller@0c000000', 'intpol-controller@0c530620', 'pinctrl@1000b000', 'pmic_irq', 'mt6370_pmu_dts']
        sprd_nodenames = ['gpio-controller@40210000', 'gpio-controller@402100a0', 'gpio-controller@402c0000', 'pmic@0', 'gpio-controller@280',
                     'interrupt-controller@14000000', 'interrupt-controller']

        dts_files = [self.__qualcomm_dts_file, self.__mtk_dts_file, self.__sprd_dts_file]
        nodenames = [qualcomm_nodenames, mtk_nodenames, sprd_nodenames]

        for i in range(len(dts_files)):        
            dts = dtsparser.Dts(dts_files[i], with_disabled_node=True)
            node_phandle = dts.get_interrup_controller_node_phandle()
            self.assertTrue(isinstance(node_phandle, dict))
            self.assertEqual(len(node_phandle), len(nodenames[i]))
            without_disabled_prop_nodenum = 0
            for node in node_phandle:
                self.assertEqual('<'+node_phandle[node]+'>', node.props['phandle'])
                self.assertTrue(node.name in nodenames[i])
                if not node.isDisabled():
                    without_disabled_prop_nodenum += 1

            dts = dtsparser.Dts(dts_files[i])
            node_phandle = dts.get_interrup_controller_node_phandle()
            self.assertTrue(isinstance(node_phandle, dict))
            self.assertLessEqual(len(node_phandle), without_disabled_prop_nodenum)
            for node in node_phandle:
                self.assertEqual('<'+node_phandle[node]+'>', node.props['phandle'])
                self.assertTrue(node.name in nodenames[i])
                self.assertFalse(node.isDisabled())

    #@unittest.skip('check output')
    def test_get_gpiocontroller_node_phandle(self):
        qualcomm_nodenames = ['pinctrl@c000', 'pinctrl@c000', 'pinctrl@c000', 'wcd_pinctrl@5', 'wcd_pinctrl', 'pinctrl@03000000']
        mtk_nodenames = ['pinctrl@1000b000']
        sprd_nodenames = ['gpio-controller@40210000',  'gpio-controller@402100a0', 'gpio-controller@402c0000', 'gpio-controller@280']
        dts_files = [self.__qualcomm_dts_file, self.__mtk_dts_file, self.__sprd_dts_file]
        nodenames = [qualcomm_nodenames, mtk_nodenames, sprd_nodenames]

        for i in range(len(dts_files)):
            dts = dtsparser.Dts(dts_files[i], with_disabled_node=True)
            node_phandle = dts.get_gpiocontroller_node_phandle()
            self.assertTrue(isinstance(node_phandle, dict))
            without_disabled_prop_nodenum = 0
            for node in node_phandle:
                self.assertEqual(''.join(['<', node_phandle[node], '>']), node.props['phandle'])
                self.assertTrue(node.name in nodenames[i])
                if not node.isDisabled():
                    without_disabled_prop_nodenum += 1

            dts = dtsparser.Dts(dts_files[i])
            node_phandle = dts.get_gpiocontroller_node_phandle()
            self.assertTrue(isinstance(node_phandle, dict))
            self.assertLessEqual(len(node_phandle), without_disabled_prop_nodenum)
            for node in node_phandle:
                self.assertFalse(node.isDisabled())
                self.assertEqual(''.join(['<', node_phandle[node], '>']), node.props['phandle'])
                self.assertTrue(node.name in nodenames[i])

    def test_get_pinctrlnode(self):
        dts_files = [self.__qualcomm_dts_file, self.__mtk_dts_file, self.__sprd_dts_file]
        for file in dts_files:
            dts = dtsparser.Dts(file)
            nodes = dts.get_pinctrlnode()
            for node in nodes:
                msg = node.dump()
                print(msg)

    #@unittest.skip('check output')
    def test_get_used_pinctrl_phandle_node(self):
        qualcomm_handles = ['0x19c', '0x19d', '0x19e', '0x19f', '0x1a2', '0x1a3', '0x216', '0x23d',
                   '0x23e', '0x240', '0x241', '0x242', '0x243', '0x244', '0x245', '0x246',
                   '0x247', '0x248', '0x249', '0x24a', '0x24b', '0x24c', '0x24d', '0x24e',
                   '0x24f', '0x250', '0x251', '0x252', '0x253', '0x254', '0x255', '0x256',
                   '0x257', '0x258', '0x259', '0x25a', '0x25b', '0x25c', '0x25d', '0x25e',
                   '0x25f', '0x260', '0x261', '0x263', '0x264', '0x265', '0x268', '0x269',
                   '0x26a', '0x26b', '0x26c', '0x26d', '0x26e', '0x26f', '0x270', '0x271',
                   '0x273', '0x274', '0x275', '0x276', '0x277', '0x278', '0x279', '0x27a',
                   '0x27b', '0x27c', '0x27d', '0x27e', '0x27f', '0x280', '0x281', '0x282',
                   '0x283', '0x284', '0x285', '0x286', '0x287', '0x288', '0x289', '0x28a',
                   '0x28b', '0x28c', '0x28d', '0x28e', '0x28f', '0x290', '0x291', '0x292',
                   '0x293', '0x294', '0x295', '0x297', '0x298', '0x29a', '0x29b', '0x29c',
                   '0x29d', '0x29e', '0x29f', '0x2a0', '0x2a1', '0x2a2', '0x2a3', '0x33',
                   '0x34', '0x35', '0x356', '0x357', '0x358', '0x35d', '0x35e', '0x36',
                   '0x363', '0x364', '0x38', '0x386', '0x387', '0x388', '0x389', '0x38a',
                   '0x38b', '0x39', '0x3a', '0x3a3', '0x3a4', '0x3a5', '0x3a6', '0x3b',
                   '0x40d', '0x40e', '0x416', '0x417', '0x418', '0x419', '0x41a', '0x41b',
                   '0x41c', '0x41d', '0x41e', '0x41f', '0x420', '0x421', '0x422', '0x423',
                   '0x424', '0x425', '0x426', '0x427', '0x428', '0x429', '0x42f', '0x430',
                   '0x431', '0x432', '0x433', '0x434', '0x43d', '0x5e9', '0x5ea', '0x5eb',
                   '0x5ec', '0x60b', '0x611', '0x612', '0x613', '0x614', '0x618', '0x619',
                   '0x61b', '0x61d', '0x61f', '0x620', '0x621', '0x622', '0x623', '0x624',
                   '0x625', '0x626', '0x627', '0x628', '0x629', '0x62a', '0x62b', '0x62c',
                   '0xac', '0xad', '0xe6', '0xe7', '0xef', '0xf1', '0xf2', '0xf3', '0xf4']
        mtk_handles = ['0x100', '0x101', '0x102', '0x103', '0x104', '0x105', '0x106', '0x107', '0x108',
                   '0x109', '0x10a', '0x10b', '0x10c', '0x10d', '0x10e', '0x10f', '0x110', '0x111',
                   '0x112', '0x113', '0xc7', '0xc8', '0xc9', '0xca', '0xcb', '0xcc', '0xcd', '0xce',
                   '0xcf', '0xd0', '0xd1', '0xd2', '0xd3', '0xd4', '0xd5', '0xd6', '0xd7', '0xd8',
                   '0xd9', '0xda', '0xdb', '0xdc', '0xdd', '0xde', '0xdf', '0xe0', '0xe1', '0xe2',
                   '0xe3', '0xe4', '0xe5', '0xe6', '0xe7', '0xe8', '0xe9', '0xea', '0xeb', '0xec',
                   '0xed', '0xee', '0xef', '0xf0', '0xf1', '0xf2', '0xf3', '0xf4', '0xf5', '0xf6',
                   '0xf7', '0xf8', '0xf9', '0xfa', '0xfb', '0xfc', '0xfd', '0xfe', '0xff']
        sprd_handles = ['0x38','0x39','0x3a','0x3b','0x3c','0x3d','0x3e','0x3f','0x40','0x41',
                   '0x42','0x43','0x44','0x45','0x46','0x47','0x48','0x49','0x4a','0x4b','0x4e']
        dts_files = [self.__qualcomm_dts_file, self.__mtk_dts_file, self.__sprd_dts_file]
        handles = [qualcomm_handles, mtk_handles, sprd_handles]
        for i in range(len(dts_files)):
            dts = dtsparser.Dts(dts_files[i], with_disabled_node=True)
            phandles_nodes = dts.get_used_pinctrl_phandle_node()
            phandles = phandles_nodes.keys()
            self.assertEqual(len(set(phandles)), len(phandles))
            self.assertEqual(len(phandles), len(handles[i]))
            without_disabled_prop_nodenum = 0
            for phandle in phandles:
                self.assertTrue(phandle in handles[i])
                for node in phandles_nodes[phandle]:
                    if not node.isDisabled():
                        without_disabled_prop_nodenum += 1
                    self.assertTrue(dts.find_node_statement_by_statementpattern('pinctrl-[0-9].*{}.*'.format(phandle)))

            dts = dtsparser.Dts(dts_files[i])
            phandles_nodes = dts.get_used_pinctrl_phandle_node()
            phandles = phandles_nodes.keys()
            self.assertEqual(len(set(phandles)), len(phandles))
            node_num = 0
            for phandle in phandles:
                self.assertTrue(phandle in handles[i])
                for node in phandles_nodes[phandle]:
                    self.assertFalse(node.isDisabled())
                    node_num += 1
                    self.assertTrue(dts.find_node_statement_by_statementpattern('pinctrl-[0-9].*{}.*'.format(phandle)))
            self.assertLessEqual(node_num, without_disabled_prop_nodenum)

    #@unittest.skip('check output')
    def test_dump_gpio_interrupt_pinctrl_usage(self):
        dts_files = [self.__qualcomm_dts_file, self.__mtk_dts_file, self.__sprd_dts_file]
        for file in dts_files:
            dts = dtsparser.Dts(file)
            msg = dts.dump_gpio_interrupt_pinctrl_usage()
            print(msg)

    #@unittest.skip('check output')
    def test_get_pinctrl_gpio_node_info(self):
        dts_files = [self.__qualcomm_dts_file, self.__mtk_dts_file, self.__sprd_dts_file]
        #dts_files = [self.__qualcomm_dts_file]
        #dts_files = [self.__mtk_dts_file]
        #dts_files = [self.__sprd_dts_file]
        for file in dts_files:
            dts = dtsparser.Dts(file)
            with self.assertRaises(ValueError):
                dts.get_pinctrl_gpio_node_info(None)
                dts.get_pinctrl_gpio_node_info('node')
            pinctrl_nodes = dts.get_pinctrlnode()
            for node in pinctrl_nodes:
                pinctrl_gpio_node_info = dts.get_pinctrl_gpio_node_info(node)
                for gpio in pinctrl_gpio_node_info:
                    for node1, node2 in pinctrl_gpio_node_info[gpio]:
                        print('{}: {}->{}'.format(gpio, node1.name, node2.name))

    #@unittest.skip('check output')
    def test_gpio_nodename_property_used(self):
        dts_files = [self.__qualcomm_dts_file, self.__mtk_dts_file, self.__sprd_dts_file]
        #dts_files = [self.__qualcomm_dts_file]
        #dts_files = [self.__mtk_dts_file]
        #dts_files = [self.__sprd_dts_file]
        for i in range(len(dts_files)):
            dts = dtsparser.Dts(dts_files[i])
            gpiocontroller_nodes = dts.get_gpiocontroller_node_phandle()
            self.assertTrue(isinstance(gpiocontroller_nodes, dict))
            for node in gpiocontroller_nodes:
                gpio_nodename_property = dts.gpio_nodename_property_used(node)
                for gpio in gpio_nodename_property:
                    for node, prop in gpio_nodename_property[gpio]:
                        print('{}: {}->{}'.format(gpio, node.name, prop))

    #@unittest.skip('check output')
    def test_interruptgpio_nodename_used(self):
        dts_files = [self.__qualcomm_dts_file, self.__mtk_dts_file, self.__sprd_dts_file]
        #dts_files = [self.__qualcomm_dts_file]
        #dts_files = [self.__mtk_dts_file]
        #dts_files = [self.__sprd_dts_file]
        for i in range(len(dts_files)):
            dts = dtsparser.Dts(dts_files[i])
            interrruptcontroller_nodes = dts.get_interrup_controller_node_phandle()
            self.assertTrue(isinstance(interrruptcontroller_nodes, dict))
            for node in interrruptcontroller_nodes:
                if 'compatible' in node.props:
                    print('{} {{\n\t\'compatible\' ={};\n}}\n'.format(node.name, node.props['compatible']))
                else:
                    print('{} {{\\n}}\n'.format(node.name))
                interrupts_node = dts.interruptgpio_nodename_used(node)
                for interrupt in interrupts_node:
                    print('{}: {}'.format(interrupt, interrupts_node[interrupt]))


#@unittest.skip('check output')
class dtsparserTest(unittest.TestCase):
    def test_dtsparser(self):
        os.system('./dtsparser.py -f sm8150-dtb-sm8150-sdx50m-mtp-overlay.dts')


if __name__ == '__main__':
    #cProfile.run('unittest.main()')
    unittest.main()
