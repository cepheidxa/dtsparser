#!/usr/bin/env python3

import unittest
import gpioparse

class NodeTest(unittest.TestCase):
        def setUp(self):
                self.__cpunode = '                cpu@100 {\
                        device_type = "cpu";\
                        compatible = "arm,cortex-a53";\
                        reg = <0x100>;\
                        enable-method = "psci";\
                        qcom,acc = <0xa>;\
                        qcom,limits-info = <0xb>;\
                        next-level-cache = <0xc>;\
                        linux,phandle = <0x6>;\
                        phandle = <0x6>;\
\
                        l2-cache {\
                                compatible = "arm,arch-cache";\
                                cache-level = <0x2>;\
                                power-domain = <0xd>;\
                                qcom,dump-size = <0x0>;\
                                linux,phandle = <0xc>;\
                                phandle = <0xc>;\
                        };\
\
                        l1-icache {\
                                compatible = "arm,arch-cache";\
                                qcom,dump-size = <0x8800>;\
                                linux,phandle = <0x1f>;\
                                phandle = <0x1f>;\
                        };\
\
                        l1-dcache {\
                                compatible = "arm,arch-cache";\
                                qcom,dump-size = <0x9000>;\
                                linux,phandle = <0x27>;\
                                phandle = <0x27>;\
                        };\
                };'
        def test_name(self):
                contents = 'name { a1 = v1; a2 = v2;}'
                node = gpioparse.Node(contents)
                self.assertEqual(node.name(), 'name')

                contents = ' name { a1 = v1; a2 = v2;}'
                node = gpioparse.Node(contents)
                self.assertEqual(node.name(), 'name')

                contents = ' name  { a1 = v1; a2 = v2;}'
                node = gpioparse.Node(contents)
                self.assertEqual(node.name(), 'name')

                contents = self.__cpunode
                node = gpioparse.Node(contents)
                self.assertEqual(node.name(), 'cpu@100')

        def test_attributes(self):
                contents = 'name { a1 = v1; a2 = v2;}'
                node = gpioparse.Node(contents)
                result_expected = {'a1': 'v1', 'a2':'v2'}
                result = node.attributes()
                self.assertEqual(len(result), len(result_expected))
                for item in result_expected:
                        self.assertEqual(result[item], result_expected[item])

                contents = self.__cpunode
                node = gpioparse.Node(contents)
                result_expected = {'device_type': '"cpu"', 'compatible':'"arm,cortex-a53"', 'reg':'<0x100>', 'enable-method':'"psci"',\
                'qcom,acc':'<0xa>', 'qcom,limits-info':'<0xb>', 'next-level-cache':'<0xc>', 'linux,phandle':'<0x6>', 'phandle':'<0x6>'}
                result = node.attributes()
                self.assertEqual(len(result), len(result_expected))
                for item in result_expected:
                        self.assertEqual(result[item], result_expected[item])

                contents = 'config { pins = "gpio24"; drive-strength = <0x2>; bias-pull-down; };'
                node = gpioparse.Node(contents)
                result_expected = {'pins': '"gpio24"', 'drive-strength':'<0x2>', 'bias-pull-down':''}
                result = node.attributes()
                self.assertEqual(len(result), len(result_expected))
                for item in result_expected:
                        self.assertEqual(result[item], result_expected[item])

                contents = 'root { model = "Qualcomm Technologies, Inc. MSM8940-PMI8940 VITA";\
                                compatible = "qcom,msm8940-mtp", "qcom,msm8940", "qcom,mtp";\
                                interrupt-parent = <0x1>;\
                                qcom,msm-id = <0x139 0x0>;}'
                node = gpioparse.Node(contents)
                result_expected = {'model': '"Qualcomm Technologies, Inc. MSM8940-PMI8940 VITA"', 'compatible':'"qcom,msm8940-mtp", "qcom,msm8940", "qcom,mtp"', 'interrupt-parent':'<0x1>', 'qcom,msm-id':'<0x139 0x0>'}
                result = node.attributes()
                self.assertEqual(len(result), len(result_expected))
                for item in result_expected:
                        self.assertEqual(result[item], result_expected[item])

        def test_find_sub_nodes_pos(self):
                contents = 'name { a1 = v1; a2 = v2;}'
                node = gpioparse.Node(contents)
                result = []
                for v in result:
                        self.assertTrue(contents[v[0]-1] == ';' or contents[v[0]-1] == '{')
                        self.assertEqual(contents[v[1]], ';')
                self.assertEqual(node.find_sub_nodes_pos(), result)

                contents = 'name { a1 = v1; name { a = v; a= v;}; a2 = v2;}'
                node = gpioparse.Node(contents)
                result = [(15, 36)]
                for v in result:
                        self.assertTrue(contents[v[0]-1] == ';' or contents[v[0]-1] == '{')
                        self.assertEqual(contents[v[1]], ';')
                self.assertEqual(node.find_sub_nodes_pos(), result)

                contents = 'name { a1 = v1; name { a = v; a= v;}; name { a = v; a= v;}; a2 = v2;}'
                node = gpioparse.Node(contents)
                result = [(15, 36), (37, 58)]
                for v in result:
                        self.assertTrue(contents[v[0]-1] == ';' or contents[v[0]-1] == '{')
                        self.assertEqual(contents[v[1]], ';')
                self.assertEqual(node.find_sub_nodes_pos(), result)

                contents = 'name { a1 = v1; name { a = v; a= v;}; a2 = v2; name { a = v; a= v;};}'
                node = gpioparse.Node(contents)
                result = [(15, 36), (46, 67)]
                for v in result:
                        self.assertTrue(contents[v[0]-1] == ';' or contents[v[0]-1] == '{')
                        self.assertEqual(contents[v[1]], ';')
                self.assertEqual(node.find_sub_nodes_pos(), result)

                contents = 'name { a1 = v1; name { a = v; name { a = v; a = "v"; }; a = v; name { a = "v"; name { a = v;}; }; a= v}; a2 = v2; name { a = v; a= v;};}'
                node = gpioparse.Node(contents)
                result = [(15, 103), (113, 134)]
                for v in result:
                        self.assertTrue(contents[v[0]-1] == ';' or contents[v[0]-1] == '{')
                        self.assertEqual(contents[v[1]], ';')
                self.assertEqual(node.find_sub_nodes_pos(), result)

                contents = 'name { a1 = v1; name { a = v; name { a = v; a = "v"; }; a = v; name { a = "v"; name { a = v;}; }; a= v}; a2 = v2; name { a = v; name { a = v; a = v; }; a= v;};}'
                node = gpioparse.Node(contents)
                result = [(15, 103), (113, 158)]
                for v in result:
                        self.assertTrue(contents[v[0]-1] == ';' or contents[v[0]-1] == '{')
                        self.assertEqual(contents[v[1]], ';')
                self.assertEqual(node.find_sub_nodes_pos(), result)

                contents = 'cpu-map { cluster0 { core0 { cpu = <0x2>; }; core1 { cpu = <0x3>; }; core2 { cpu = <0x4>; }; core3 { cpu = <0x5>; }; }; cluster1 { core0 { cpu = <0x6>; }; core1 { cpu = <0x7>; }; core2 { cpu = <0x8>; }; core3 { cpu = <0x9>; }; }; }'
                node = gpioparse.Node(contents)
                result = [(9, 118), (119, 228)]
                for v in result:
                        self.assertTrue(contents[v[0]-1] == ';' or contents[v[0]-1] == '{')
                        self.assertEqual(contents[v[1]], ';')
                self.assertEqual(node.find_sub_nodes_pos(), result)

        def test_find_sub_nodes(self):
                return
                contents = self.__cpunode
                node = gpioparse.Node(contents)
                #node.dump()
        def test_dts_parser(self):
                root = gpioparse.dts_parser('a.dts')
                root.dump()

if __name__ == '__main__':
        unittest.main()
                
                
