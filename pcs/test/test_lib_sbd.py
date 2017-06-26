from __future__ import (
    absolute_import,
    division,
    print_function,
)

import json
from pcs.test.tools.misc import outdent
from pcs.test.tools.pcs_unittest import TestCase, mock, skip

from pcs.test.tools.assertions import (
    assert_raise_library_error,
    assert_report_item_list_equal,
)
from pcs.test.tools.custom_mock import MockLibraryReportProcessor

from pcs import settings
from pcs.common import report_codes
from pcs.lib import reports
from pcs.lib.errors import (
    ReportItemSeverity as Severities,
    LibraryError,
)
from pcs.lib.node import NodeAddresses
from pcs.lib.external import (
    CommandRunner,
    NodeCommunicationException,
    NodeCommunicator,
    NodeConnectionException,
)
import pcs.lib.sbd as lib_sbd
from pcs.lib.corosync.config_facade import ConfigFacade as CorosyncConfigFacade


class TestException(Exception):
    pass


class EvenNumberOfNodesAndNoQdevice(TestCase):
    def setUp(self):
        self.mock_corosync_conf = mock.MagicMock(spec_set=CorosyncConfigFacade)

    def _set_ret_vals(self, nodes, qdevice):
        self.mock_corosync_conf.get_nodes.return_value = nodes
        self.mock_corosync_conf.has_quorum_device.return_value = qdevice

    def test_even_num_no_qdevice(self):
        self._set_ret_vals([1, 2], False)
        self.assertTrue(lib_sbd._even_number_of_nodes_and_no_qdevice(
            self.mock_corosync_conf
        ))

    def test_even_num_qdevice(self):
        self._set_ret_vals([1, 2], True)
        self.assertFalse(lib_sbd._even_number_of_nodes_and_no_qdevice(
            self.mock_corosync_conf
        ))

    def test_odd_num_no_qdevice(self):
        self._set_ret_vals([1, 2, 3], False)
        self.assertFalse(lib_sbd._even_number_of_nodes_and_no_qdevice(
            self.mock_corosync_conf
        ))

    def test_odd_num_qdevice(self):
        self._set_ret_vals([1, 2, 3], True)
        self.assertFalse(lib_sbd._even_number_of_nodes_and_no_qdevice(
            self.mock_corosync_conf
        ))

    def test_even_num_no_qdevice_plus_one(self):
        self._set_ret_vals([1, 2], False)
        self.assertFalse(lib_sbd._even_number_of_nodes_and_no_qdevice(
            self.mock_corosync_conf, 1
        ))

    def test_even_num_qdevice_plus_one(self):
        self._set_ret_vals([1, 2], True)
        self.assertFalse(lib_sbd._even_number_of_nodes_and_no_qdevice(
            self.mock_corosync_conf, 1
        ))

    def test_odd_num_no_qdevice_plus_one(self):
        self._set_ret_vals([1, 2, 3], False)
        self.assertTrue(lib_sbd._even_number_of_nodes_and_no_qdevice(
            self.mock_corosync_conf, 1
        ))

    def test_odd_num_qdevice_plus_one(self):
        self._set_ret_vals([1, 2, 3], True)
        self.assertFalse(lib_sbd._even_number_of_nodes_and_no_qdevice(
            self.mock_corosync_conf, 1
        ))


@mock.patch("pcs.lib.sbd.is_device_set_local")
@mock.patch("pcs.lib.sbd.is_sbd_enabled")
@mock.patch("pcs.lib.sbd.is_sbd_installed")
@mock.patch("pcs.lib.sbd._even_number_of_nodes_and_no_qdevice")
class IsAutoTieBreakerNeededTest(TestCase):
    def setUp(self):
        self.runner = "runner"
        self.corosync_conf_facade = "facade"
        self.node_num_modifier = 1
        self.mock_nodes_and_qdevice = None
        self.mock_sbd_installed = None
        self.mock_sbd_enabled = None
        self.mock_device_set = None

    def set_mocks(
        self, mock_nodes_and_qdevice, mock_sbd_installed, mock_sbd_enabled,
        mock_device_set
    ):
        self.mock_nodes_and_qdevice = mock_nodes_and_qdevice
        self.mock_sbd_installed = mock_sbd_installed
        self.mock_sbd_enabled = mock_sbd_enabled
        self.mock_device_set = mock_device_set

    def common_test(
        self, nodes_and_qdevice, sbd_installed, sbd_enabled, device_set, result
    ):
        self.mock_nodes_and_qdevice.return_value = nodes_and_qdevice
        self.mock_sbd_installed.return_value = sbd_installed
        self.mock_sbd_enabled.return_value = sbd_enabled
        self.mock_device_set.return_value = device_set
        self.assertEqual(
            lib_sbd.is_auto_tie_breaker_needed(
                self.runner, self.corosync_conf_facade, self.node_num_modifier
            ),
            result
        )
        self.mock_nodes_and_qdevice.assert_called_once_with(
            self.corosync_conf_facade, self.node_num_modifier
        )

    def test_device_set(
        self, mock_nodes_and_qdevice, mock_sbd_installed, mock_sbd_enabled,
        mock_device_set
    ):
        self.set_mocks(
            mock_nodes_and_qdevice, mock_sbd_installed, mock_sbd_enabled,
            mock_device_set
        )
        self.common_test(True, True, True, True, False)

    def test_no_device(
        self, mock_nodes_and_qdevice, mock_sbd_installed, mock_sbd_enabled,
        mock_device_set
    ):
        self.set_mocks(
            mock_nodes_and_qdevice, mock_sbd_installed, mock_sbd_enabled,
            mock_device_set
        )
        self.common_test(True, True, True, False, True)

    def test_no_device_with_qdevice(
        self, mock_nodes_and_qdevice, mock_sbd_installed, mock_sbd_enabled,
        mock_device_set
    ):
        self.set_mocks(
            mock_nodes_and_qdevice, mock_sbd_installed, mock_sbd_enabled,
            mock_device_set
        )
        self.common_test(False, True, True, False, False)

    def test_sbd_disabled(
        self, mock_nodes_and_qdevice, mock_sbd_installed, mock_sbd_enabled,
        mock_device_set
    ):
        self.set_mocks(
            mock_nodes_and_qdevice, mock_sbd_installed, mock_sbd_enabled,
            mock_device_set
        )
        self.common_test(True, True, False, False, False)


@mock.patch("pcs.lib.sbd.is_auto_tie_breaker_needed")
class AtbHasToBeEnabledTest(TestCase):
    def setUp(self):
        self.mock_runner = "runner"
        self.mock_conf = mock.MagicMock(spec_set=CorosyncConfigFacade)

    def test_atb_needed_is_enabled(self, mock_is_needed):
        mock_is_needed.return_value = True
        self.mock_conf.is_enabled_auto_tie_breaker.return_value = True
        self.assertFalse(lib_sbd.atb_has_to_be_enabled(
            self.mock_runner, self.mock_conf, 1
        ))
        self.mock_conf.is_enabled_auto_tie_breaker.assert_called_once_with()
        mock_is_needed.assert_not_called()

    def test_atb_needed_is_disabled(self, mock_is_needed):
        mock_is_needed.return_value = True
        self.mock_conf.is_enabled_auto_tie_breaker.return_value = False
        self.assertTrue(lib_sbd.atb_has_to_be_enabled(
            self.mock_runner, self.mock_conf, -1
        ))
        self.mock_conf.is_enabled_auto_tie_breaker.assert_called_once_with()
        mock_is_needed.assert_called_once_with(
            self.mock_runner, self.mock_conf, -1
        )

    def test_atb_not_needed_is_enabled(self, mock_is_needed):
        mock_is_needed.return_value = False
        self.mock_conf.is_enabled_auto_tie_breaker.return_value = True
        self.assertFalse(lib_sbd.atb_has_to_be_enabled(
            self.mock_runner, self.mock_conf, 2
        ))
        self.mock_conf.is_enabled_auto_tie_breaker.assert_called_once_with()
        mock_is_needed.assert_not_called()

    def test_atb_not_needed_is_disabled(self, mock_is_needed):
        mock_is_needed.return_value = False
        self.mock_conf.is_enabled_auto_tie_breaker.return_value = False
        self.assertFalse(lib_sbd.atb_has_to_be_enabled(
            self.mock_runner, self.mock_conf, -2
        ))
        self.mock_conf.is_enabled_auto_tie_breaker.assert_called_once_with()
        mock_is_needed.assert_called_once_with(
            self.mock_runner, self.mock_conf, -2
        )


@skip("TODO: rewrite for pcs.lib.communication.sbd.CheckSbd")
class CheckSbdTest(TestCase):
    def test_success(self):
        mock_communicator = mock.MagicMock(spec_set=NodeCommunicator)
        node = NodeAddresses("node1")
        lib_sbd.check_sbd(
            mock_communicator, node, "/dev/watchdog", ["/dev/sdb1", "/dev/sdc"]
        )
        mock_communicator.call_node.assert_called_once_with(
            node, "remote/check_sbd", "watchdog=%2Fdev%2Fwatchdog&" +\
            "device_list=%5B%22%2Fdev%2Fsdb1%22%2C+%22%2Fdev%2Fsdc%22%5D"
        )

@skip("TODO: rewrite for pcs.lib.communication.sbd.CheckSbd")
@mock.patch("pcs.lib.sbd.check_sbd")
class CheckSbdOnNodeTest(TestCase):
    def setUp(self):
        self.mock_com = mock.MagicMock(spec_set=NodeCommunicator)
        self.mock_rep = MockLibraryReportProcessor()
        self.node = NodeAddresses("node1")
        self.device_list = ["/dev/sdb1", "/dev/sdc"]

    def test_success(self, mock_check_sbd):
        mock_check_sbd.return_value = json.dumps({
            "sbd": {
                "installed": True
            },
            "watchdog": {
                "exist": True
            }
        })
        # if no exception was raised, it's fine
        lib_sbd.check_sbd_on_node(
            self.mock_rep, self.mock_com, self.node, "watchdog",
            self.device_list
        )
        mock_check_sbd.assert_called_once_with(
            self.mock_com, self.node, "watchdog", self.device_list
        )
        assert_report_item_list_equal(
            self.mock_rep.report_item_list,
            [(
                Severities.INFO,
                report_codes.SBD_CHECK_SUCCESS,
                {"node": self.node.label}
            )]
        )

    def test_unable_to_connect(self, mock_check_sbd):
        mock_check_sbd.side_effect = NodeConnectionException(
            self.node.label, "command", "reason"
        )
        self.assertRaises(
            NodeCommunicationException,
            lambda: lib_sbd.check_sbd_on_node(
                self.mock_rep, self.mock_com, self.node, "watchdog",
                self.device_list
            )
        )
        mock_check_sbd.assert_called_once_with(
            self.mock_com, self.node, "watchdog", self.device_list
        )
        self.assertEqual(0, len(self.mock_rep.report_item_list))

    def test_data_parsing_error(self, mock_check_sbd):
        mock_check_sbd.return_value = "invalid JSON"
        assert_raise_library_error(
            lambda: lib_sbd.check_sbd_on_node(
                self.mock_rep, self.mock_com, self.node, "watchdog",
                self.device_list
            ),
            (
                Severities.ERROR,
                report_codes.INVALID_RESPONSE_FORMAT,
                {"node": self.node.label}
            )
        )
        mock_check_sbd.assert_called_once_with(
            self.mock_com, self.node, "watchdog", self.device_list
        )
        self.assertEqual(0, len(self.mock_rep.report_item_list))

    def test_sbd_not_installed(self, mock_check_sbd):
        mock_check_sbd.return_value = json.dumps({
            "sbd": {
                "installed": False
            },
            "watchdog": {
                "exist": True
            }
        })
        assert_raise_library_error(
            lambda: lib_sbd.check_sbd_on_node(
                self.mock_rep, self.mock_com, self.node, "watchdog",
                self.device_list
            ),
            (
                Severities.ERROR,
                report_codes.SBD_NOT_INSTALLED,
                {"node": self.node.label}
            )
        )
        mock_check_sbd.assert_called_once_with(
            self.mock_com, self.node, "watchdog", self.device_list
        )
        self.assertEqual(0, len(self.mock_rep.report_item_list))

    def test_watchdog_does_not_exist(self, mock_check_sbd):
        mock_check_sbd.return_value = json.dumps({
            "sbd": {
                "installed": True
            },
            "watchdog": {
                "exist": False
            }
        })
        assert_raise_library_error(
            lambda: lib_sbd.check_sbd_on_node(
                self.mock_rep, self.mock_com, self.node, "watchdog",
                self.device_list
            ),
            (
                Severities.ERROR,
                report_codes.WATCHDOG_NOT_FOUND,
                {"node": self.node.label}
            )
        )
        mock_check_sbd.assert_called_once_with(
            self.mock_com, self.node, "watchdog", self.device_list
        )
        self.assertEqual(0, len(self.mock_rep.report_item_list))

    def test_watchdog_does_not_exist_and_sbd_not_installed(
            self, mock_check_sbd
    ):
        mock_check_sbd.return_value = json.dumps({
            "sbd": {
                "installed": False
            },
            "watchdog": {
                "exist": False
            }
        })
        assert_raise_library_error(
            lambda: lib_sbd.check_sbd_on_node(
                self.mock_rep, self.mock_com, self.node, "watchdog",
                self.device_list
            ),
            (
                Severities.ERROR,
                report_codes.WATCHDOG_NOT_FOUND,
                {"node": self.node.label}
            ),
            (
                Severities.ERROR,
                report_codes.SBD_NOT_INSTALLED,
                {"node": self.node.label}
            )
        )
        mock_check_sbd.assert_called_once_with(
            self.mock_com, self.node, "watchdog", self.device_list
        )
        self.assertEqual(0, len(self.mock_rep.report_item_list))

    def test_one_device_does_not_exist(self, mock_check_sbd):
        mock_check_sbd.return_value = json.dumps({
            "sbd": {
                "installed": True
            },
            "watchdog": {
                "exist": True
            },
            "device_list": [
                {
                    "path": "/dev/sbd",
                    "exist": True,
                    "block_device": True,
                },
                {
                    "path": "/dev/sdc",
                    "exist": False,
                    "block_device": False,
                }
            ]
        })
        assert_raise_library_error(
            lambda: lib_sbd.check_sbd_on_node(
                self.mock_rep, self.mock_com, self.node, "watchdog",
                self.device_list
            ),
            (
                Severities.ERROR,
                report_codes.SBD_DEVICE_DOES_NOT_EXIST,
                {
                    "device": "/dev/sdc",
                    "node": self.node.label,
                }
            )
        )
        mock_check_sbd.assert_called_once_with(
            self.mock_com, self.node, "watchdog", self.device_list
        )
        self.assertEqual(0, len(self.mock_rep.report_item_list))

    def test_devices_issues(self, mock_check_sbd):
        mock_check_sbd.return_value = json.dumps({
            "sbd": {
                "installed": True
            },
            "watchdog": {
                "exist": True
            },
            "device_list": [
                {
                    "path": "/dev/sdb",
                    "exist": True,
                    "block_device": False,
                },
                {
                    "path": "/dev/sdc",
                    "exist": False,
                    "block_device": False,
                }
            ]
        })
        assert_raise_library_error(
            lambda: lib_sbd.check_sbd_on_node(
                self.mock_rep, self.mock_com, self.node, "watchdog",
                self.device_list
            ),
            (
                Severities.ERROR,
                report_codes.SBD_DEVICE_DOES_NOT_EXIST,
                {
                    "device": "/dev/sdc",
                    "node": self.node.label,
                }
            ),
            (
                Severities.ERROR,
                report_codes.SBD_DEVICE_IS_NOT_BLOCK_DEVICE,
                {
                    "device": "/dev/sdb",
                    "node": self.node.label,
                }
            )
        )
        mock_check_sbd.assert_called_once_with(
            self.mock_com, self.node, "watchdog", self.device_list
        )
        self.assertEqual(0, len(self.mock_rep.report_item_list))

    def test_invalid_response_format(self, mock_check_sbd):
        mock_check_sbd.return_value = json.dumps({
            "not_sbd": {
                "installed": False
            },
            "watchdog": {
                "exist": False
            }
        })
        assert_raise_library_error(
            lambda: lib_sbd.check_sbd_on_node(
                self.mock_rep, self.mock_com, self.node, "watchdog",
                self.device_list
            ),
            (
                Severities.ERROR,
                report_codes.INVALID_RESPONSE_FORMAT,
                {"node": self.node.label}
            )
        )
        mock_check_sbd.assert_called_once_with(
            self.mock_com, self.node, "watchdog", self.device_list
        )
        self.assertEqual(0, len(self.mock_rep.report_item_list))

@skip("TODO: rewrite for pcs.lib.communication.sbd.CheckSbd")
@mock.patch("pcs.lib.sbd._run_parallel_and_raise_lib_error_on_failure")
class CheckSbdOnAllNodesTest(TestCase):
    def test_success(self, mock_func):
        mock_com = mock.MagicMock(spec_set=NodeCommunicator)
        mock_rep = MockLibraryReportProcessor()
        node_list = [NodeAddresses("node" + str(i)) for i in range(2)]
        data = {
            node_list[0]: {
                "watchdog": "/dev/watchdog1",
                "device_list": ["/dev/sdb", "/dev/vda1"],
            },
            node_list[1]: {
                "watchdog": "/dev/watchdog2",
                "device_list": ["/dev/sda2"],
            }
        }
        lib_sbd.check_sbd_on_all_nodes(mock_rep, mock_com, data)
        items = sorted(data.items())
        mock_func.assert_called_once_with(
            lib_sbd.check_sbd_on_node,
            [
                (
                    [
                        mock_rep, mock_com, node, data["watchdog"],
                        data["device_list"]
                    ],
                    {}
                )
                for node, data in items
            ]
        )

@skip("TODO: rewrite for pcs.lib.communication.sbd.SetSbdConfig")
class SetSbdConfigTest(TestCase):
    def test_success(self):
        mock_communicator = mock.MagicMock(spec_set=NodeCommunicator)
        node = NodeAddresses("node1")
        cfg = """# This file has been generated by pcs.
SBD_OPTS="-n node1"
SBD_WATCHDOG_DEV=/dev/watchdog
SBD_WATCHDOG_TIMEOUT=0
"""
        lib_sbd.set_sbd_config(mock_communicator, node, cfg)
        cfg_url_encoded = "%23+This+file+has+been+generated+by+" \
            "pcs.%0ASBD_OPTS%3D%22-n+node1%22%0ASBD_WATCHDOG_DEV%3D%2Fdev%2" \
            "Fwatchdog%0ASBD_WATCHDOG_TIMEOUT%3D0%0A"
        mock_communicator.call_node.assert_called_once_with(
            node, "remote/set_sbd_config", "config=" + cfg_url_encoded
        )

@skip("TODO: rewrite for pcs.lib.communication.sbd.SetSbdConfig")
@mock.patch("pcs.lib.sbd.set_sbd_config")
class SetSbdConfigOnNodeTest(TestCase):
    def setUp(self):
        self.mock_com = mock.MagicMock(spec_set=NodeCommunicator)
        self.mock_rep = MockLibraryReportProcessor()
        self.node = NodeAddresses("node1")

    def test_success(self, mock_set_sbd_cfg):
        cfg_in = {
            "SBD_WATCHDOG_DEV": "/dev/watchdog",
            "SBD_WATCHDOG_TIMEOUT": "0"
        }
        cfg_out = """# This file has been generated by pcs.
SBD_OPTS="-n node1"
SBD_WATCHDOG_DEV=/my/watchdog
SBD_WATCHDOG_TIMEOUT=0
"""
        lib_sbd.set_sbd_config_on_node(
            self.mock_rep, self.mock_com, self.node, cfg_in, "/my/watchdog"
        )
        mock_set_sbd_cfg.assert_called_once_with(
            self.mock_com, self.node, cfg_out
        )
        assert_report_item_list_equal(
            self.mock_rep.report_item_list,
            [(
                Severities.INFO,
                report_codes.SBD_CONFIG_ACCEPTED_BY_NODE,
                {"node": self.node.label}
            )]
        )

    def test_with_devices(self, mock_set_sbd_cfg):
        cfg_in = {
            "SBD_WATCHDOG_DEV": "/dev/watchdog",
            "SBD_WATCHDOG_TIMEOUT": "0",
        }
        cfg_out = """# This file has been generated by pcs.
SBD_DEVICE="/dev/sdb;/dev/vda"
SBD_OPTS="-n node1"
SBD_WATCHDOG_DEV=/my/watchdog
SBD_WATCHDOG_TIMEOUT=0
"""
        lib_sbd.set_sbd_config_on_node(
            self.mock_rep, self.mock_com, self.node, cfg_in, "/my/watchdog",
            ["/dev/sdb", "/dev/vda"]
        )
        mock_set_sbd_cfg.assert_called_once_with(
            self.mock_com, self.node, cfg_out
        )
        assert_report_item_list_equal(
            self.mock_rep.report_item_list,
            [(
                Severities.INFO,
                report_codes.SBD_CONFIG_ACCEPTED_BY_NODE,
                {"node": self.node.label}
            )]
        )

@skip("TODO: rewrite for pcs.lib.communication.sbd.SetSbdConfig")
@mock.patch("pcs.lib.sbd._run_parallel_and_raise_lib_error_on_failure")
class SetSbdConfigOnAllNodesTest(TestCase):
    def test_success(self, mock_func):
        mock_com = mock.MagicMock(spec_set=NodeCommunicator)
        mock_rep = MockLibraryReportProcessor()
        watchdog_dict = dict([
            (NodeAddresses("node" + str(i)), "/dev/watchdog" + str(i))
            for i in range(5)
        ])
        device_dict = dict([
            (NodeAddresses("node" + str(i)), ["/dev/sdb" + str(i)])
            for i in range(5)
        ])
        node_list = list(watchdog_dict.keys())
        config = {
            "opt1": "val1",
            "opt2": "val2"
        }
        lib_sbd.set_sbd_config_on_all_nodes(
            mock_rep, mock_com, node_list, config, watchdog_dict, device_dict
        )
        mock_func.assert_called_once_with(
            lib_sbd.set_sbd_config_on_node,
            [
                (
                    [
                        mock_rep, mock_com, node, config, watchdog_dict[node],
                        device_dict[node]
                    ], {}
                )
                for node in node_list
            ]
        )

@skip("TODO: rewrite for pcs.lib.communication.sbd.EnableSbdService")
class EnableSbdServiceTest(TestCase):
    def test_success(self):
        mock_communicator = mock.MagicMock(spec_set=NodeCommunicator)
        node = NodeAddresses("node1")
        lib_sbd.enable_sbd_service(mock_communicator, node)
        mock_communicator.call_node.assert_called_once_with(
            node, "remote/sbd_enable", None
        )

@skip("TODO: rewrite for pcs.lib.communication.sbd.EnableSbdService")
class EnableSbdServiceOnNodeTest(TestCase):
    def setUp(self):
        self.mock_com = mock.MagicMock(spec_set=NodeCommunicator)
        self.mock_rep = MockLibraryReportProcessor()
        self.node = NodeAddresses("node1")

    @mock.patch("pcs.lib.sbd.enable_sbd_service")
    def test_success(self, mock_enable_sbd):
        lib_sbd.enable_sbd_service_on_node(
            self.mock_rep, self.mock_com, self.node
        )
        mock_enable_sbd.assert_called_once_with(self.mock_com, self.node)
        assert_report_item_list_equal(
            self.mock_rep.report_item_list,
            [(
                Severities.INFO,
                report_codes.SERVICE_ENABLE_SUCCESS,
                {
                    "service": "sbd",
                    "node": self.node.label
                }
            )]
        )

@skip("TODO: rewrite for pcs.lib.communication.sbd.EnableSbdService")
@mock.patch("pcs.lib.sbd._run_parallel_and_raise_lib_error_on_failure")
class EnableSbdServiceOnAllNodes(TestCase):
    def test_success(self, mock_func):
        mock_com = mock.MagicMock(spec_set=NodeCommunicator)
        mock_rep = MockLibraryReportProcessor()
        node_list = [NodeAddresses("node" + str(i)) for i in range(5)]
        lib_sbd.enable_sbd_service_on_all_nodes(mock_rep, mock_com, node_list)
        mock_func.assert_called_once_with(
            lib_sbd.enable_sbd_service_on_node,
            [([mock_rep, mock_com, node], {}) for node in node_list]
        )

@skip("TODO: rewrite for pcs.lib.communication.sbd.DisableSbdService")
class DisableSbdServiceTest(TestCase):
    def test_success(self):
        mock_communicator = mock.MagicMock(spec_set=NodeCommunicator)
        node = NodeAddresses("node1")
        lib_sbd.disable_sbd_service(mock_communicator, node)
        mock_communicator.call_node.assert_called_once_with(
            node, "remote/sbd_disable", None
        )

@skip("TODO: rewrite for pcs.lib.communication.sbd.DisableSbdService")
class DisableSbdServiceOnNodeTest(TestCase):
    def setUp(self):
        self.mock_com = mock.MagicMock(spec_set=NodeCommunicator)
        self.mock_rep = MockLibraryReportProcessor()
        self.node = NodeAddresses("node1")

    @mock.patch("pcs.lib.sbd.disable_sbd_service")
    def test_success(self, mock_disable_sbd):
        lib_sbd.disable_sbd_service_on_node(
            self.mock_rep, self.mock_com, self.node
        )
        mock_disable_sbd.assert_called_once_with(self.mock_com, self.node)
        assert_report_item_list_equal(
            self.mock_rep.report_item_list,
            [(
                Severities.INFO,
                report_codes.SERVICE_DISABLE_SUCCESS,
                {
                    "service": "sbd",
                    "node": self.node.label
                }
            )]
        )

@skip("TODO: rewrite for pcs.lib.communication.sbd.DisableSbdService")
@mock.patch("pcs.lib.sbd._run_parallel_and_raise_lib_error_on_failure")
class DisableSbdServiceOnAllNodes(TestCase):
    def test_success(self, mock_func):
        mock_com = mock.MagicMock(spec_set=NodeCommunicator)
        mock_rep = MockLibraryReportProcessor()
        node_list = [NodeAddresses("node" + str(i)) for i in range(5)]
        lib_sbd.disable_sbd_service_on_all_nodes(mock_rep, mock_com, node_list)
        mock_func.assert_called_once_with(
            lib_sbd.disable_sbd_service_on_node,
            [([mock_rep, mock_com, node], {}) for node in node_list]
        )

@skip(
    "TODO: rewrite for "
    "pcs.lib.communication.sbd.SetStonithWatchdogTimeoutToZero"
)
class SetStonithWatchdogTimeoutToZeroTest(TestCase):
    def test_success(self):
        mock_communicator = mock.MagicMock(spec_set=NodeCommunicator)
        node = NodeAddresses("node1")
        lib_sbd.set_stonith_watchdog_timeout_to_zero(mock_communicator, node)
        mock_communicator.call_node.assert_called_once_with(
            node, "remote/set_stonith_watchdog_timeout_to_zero", None
        )

@skip(
    "TODO: rewrite for "
    "pcs.lib.communication.sbd.SetStonithWatchdogTimeoutToZero"
)
@mock.patch("pcs.lib.sbd.set_stonith_watchdog_timeout_to_zero")
class SetStonithWatchdogTimeoutToZeroOnAllNodesTest(TestCase):
    def setUp(self):
        self.mock_com = mock.MagicMock(spec_set=NodeCommunicator)
        self.node_list = [NodeAddresses("node" + str(i)) for i in range(5)]

    def test_success(self, mock_func):
        lib_sbd.set_stonith_watchdog_timeout_to_zero_on_all_nodes(
            self.mock_com, self.node_list
        )
        func_calls = [mock.call(self.mock_com, node) for node in self.node_list]
        self.assertEqual(mock_func.call_count, len(func_calls))
        mock_func.assert_has_calls(func_calls)

    def test_communication_error(self, mock_func):
        def raiser(_, node):
            if node == self.node_list[1]:
                raise NodeConnectionException(
                    self.node_list[1], "command", "reason"
                )
            elif node == self.node_list[4]:
                raise NodeCommunicationException(
                    self.node_list[4], "command", "reason"
                )

        mock_func.side_effect = raiser
        assert_raise_library_error(
            lambda: lib_sbd.set_stonith_watchdog_timeout_to_zero_on_all_nodes(
                self.mock_com, self.node_list
            ),
            (
                Severities.ERROR,
                report_codes.NODE_COMMUNICATION_ERROR_UNABLE_TO_CONNECT,
                {
                    "node": self.node_list[1],
                    "command": "command",
                    "reason": "reason"
                }
            ),
            (
                Severities.ERROR,
                report_codes.NODE_COMMUNICATION_ERROR,
                {
                    "node": self.node_list[4],
                    "command": "command",
                    "reason": "reason"
                }
            )
        )
        func_calls = [mock.call(self.mock_com, node) for node in self.node_list]
        self.assertEqual(mock_func.call_count, len(func_calls))
        mock_func.assert_has_calls(func_calls)

@skip(
    "TODO: rewrite for pcs.lib.communication.sbd.RemoveStonithWatchdogTimeout"
)
class RemoveStonithWatchdogTimeoutTest(TestCase):
    def test_success(self):
        mock_communicator = mock.MagicMock(spec_set=NodeCommunicator)
        node = NodeAddresses("node1")
        lib_sbd.remove_stonith_watchdog_timeout(mock_communicator, node)
        mock_communicator.call_node.assert_called_once_with(
            node, "remote/remove_stonith_watchdog_timeout", None
        )

@skip(
    "TODO: rewrite for pcs.lib.communication.sbd.RemoveStonithWatchdogTimeout"
)
@mock.patch("pcs.lib.sbd.remove_stonith_watchdog_timeout")
class RemoveStonithWatchdogTimeoutOnAllNodesTest(TestCase):
    def setUp(self):
        self.mock_com = mock.MagicMock(spec_set=NodeCommunicator)
        self.node_list = [NodeAddresses("node" + str(i)) for i in range(5)]

    def test_success(self, mock_func):
        lib_sbd.remove_stonith_watchdog_timeout_on_all_nodes(
            self.mock_com, self.node_list
        )
        func_calls = [mock.call(self.mock_com, node) for node in self.node_list]
        self.assertEqual(mock_func.call_count, len(func_calls))
        mock_func.assert_has_calls(func_calls)

    def test_communication_error(self, mock_func):
        def raiser(_, node):
            if node == self.node_list[1]:
                raise NodeConnectionException(
                    self.node_list[1], "command", "reason"
                )
            elif node == self.node_list[4]:
                raise NodeCommunicationException(
                    self.node_list[4], "command", "reason"
                )

        mock_func.side_effect = raiser
        assert_raise_library_error(
            lambda: lib_sbd.remove_stonith_watchdog_timeout_on_all_nodes(
                self.mock_com, self.node_list
            ),
            (
                Severities.ERROR,
                report_codes.NODE_COMMUNICATION_ERROR_UNABLE_TO_CONNECT,
                {
                    "node": self.node_list[1],
                    "command": "command",
                    "reason": "reason"
                }
            ),
            (
                Severities.ERROR,
                report_codes.NODE_COMMUNICATION_ERROR,
                {
                    "node": self.node_list[4],
                    "command": "command",
                    "reason": "reason"
                }
            )
        )
        func_calls = [mock.call(self.mock_com, node) for node in self.node_list]
        self.assertEqual(mock_func.call_count, len(func_calls))
        mock_func.assert_has_calls(func_calls)

@skip("TODO: rewrite for pcs.lib.communication.sbd.GetSbdStatus")
class GetSbdConfigTest(TestCase):
    def test_success(self):
        mock_communicator = mock.MagicMock(spec_set=NodeCommunicator)
        node = NodeAddresses("node1")
        lib_sbd.get_sbd_config(mock_communicator, node)
        mock_communicator.call_node.assert_called_once_with(
            node, "remote/get_sbd_config", None
        )


@mock.patch("pcs.lib.external.is_systemctl")
class GetSbdServiceNameTest(TestCase):
    def test_systemctl(self, mock_is_systemctl):
        mock_is_systemctl.return_value = True
        self.assertEqual("sbd", lib_sbd.get_sbd_service_name())
        mock_is_systemctl.assert_called_once_with()

    def test_not_systemctl(self, mock_is_systemctl):
        mock_is_systemctl.return_value = False
        self.assertEqual("sbd_helper", lib_sbd.get_sbd_service_name())
        mock_is_systemctl.assert_called_once_with()


@mock.patch("pcs.lib.sbd.get_sbd_service_name")
@mock.patch("pcs.lib.external.is_service_enabled")
class IsSbdEnabledTest(TestCase):
    def test_success(self, mock_is_service_enabled, mock_sbd_name):
        mock_obj = mock.MagicMock()
        mock_is_service_enabled.return_value = True
        mock_sbd_name.return_value = "sbd"
        self.assertTrue(lib_sbd.is_sbd_enabled(mock_obj))
        mock_is_service_enabled.assert_called_once_with(mock_obj, "sbd")
        mock_sbd_name.assert_called_once_with()


@mock.patch("pcs.lib.sbd.get_sbd_service_name")
@mock.patch("pcs.lib.external.is_service_installed")
class IsSbdInstalledTest(TestCase):
    def test_installed(self, mock_is_service_installed, mock_sbd_name):
        mock_obj = mock.MagicMock()
        mock_is_service_installed.return_value = True
        mock_sbd_name.return_value = "sbd"
        self.assertTrue(lib_sbd.is_sbd_installed(mock_obj))
        mock_is_service_installed.assert_called_once_with(mock_obj, "sbd")
        mock_sbd_name.assert_called_once_with()

    def test_not_installed(self, mock_is_service_installed, mock_sbd_name):
        mock_obj = mock.MagicMock()
        mock_is_service_installed.return_value = False
        mock_sbd_name.return_value = "sbd"
        self.assertFalse(lib_sbd.is_sbd_installed(mock_obj))
        mock_is_service_installed.assert_called_once_with(mock_obj, "sbd")
        mock_sbd_name.assert_called_once_with()


class InitializeBlockDeviceTest(TestCase):
    def setUp(self):
        self.mock_runner = mock.MagicMock()
        self.mock_rep = MockLibraryReportProcessor()

    def test_success(self):
        device_list = ["/dev/sdb", "/dev/vda"]
        option_dict = {
            "watchdog-timeout": "10", # -1
            "loop-timeout": "1", # -3
        }
        self.mock_runner.run.return_value = "", "", 0
        lib_sbd.initialize_block_devices(
            self.mock_rep, self.mock_runner, device_list, option_dict
        )
        cmd = [
            settings.sbd_binary, "-d", "/dev/sdb", "-d", "/dev/vda", "-3", "1",
            "-1", "10", "create"
        ]
        self.mock_runner.run.assert_called_once_with(cmd)
        assert_report_item_list_equal(
            self.mock_rep.report_item_list,
            [
                (
                    Severities.INFO,
                    report_codes.SBD_DEVICE_INITIALIZATION_STARTED,
                    {"device_list": device_list}
                ),
                (
                    Severities.INFO,
                    report_codes.SBD_DEVICE_INITIALIZATION_SUCCESS,
                    {"device_list": device_list}
                ),
            ]
        )

    def test_failed(self):
        device_list = ["/dev/sdb", "/dev/vda"]
        option_dict = {
            "watchdog-timeout": "10", # -1
            "loop-timeout": "1", # -3
        }
        error_msg = "error"
        self.mock_runner.run.return_value = "", error_msg, 1
        assert_raise_library_error(
            lambda: lib_sbd.initialize_block_devices(
                self.mock_rep, self.mock_runner, device_list, option_dict
            ),
            (
                Severities.ERROR,
                report_codes.SBD_DEVICE_INITIALIZATION_ERROR,
                {
                    "device_list": device_list,
                    "reason": error_msg,
                }
            )
        )
        cmd = [
            settings.sbd_binary, "-d", "/dev/sdb", "-d", "/dev/vda", "-3", "1",
            "-1", "10", "create"
        ]
        self.mock_runner.run.assert_called_once_with(cmd)
        assert_report_item_list_equal(
            self.mock_rep.report_item_list,
            [(
                Severities.INFO,
                report_codes.SBD_DEVICE_INITIALIZATION_STARTED,
                {"device_list": device_list}
            )]
        )


@mock.patch("os.path.exists")
@mock.patch("pcs.lib.sbd.get_local_sbd_config")
class GetLocalSbdDeviceListTest(TestCase):
    def test_device_not_defined(self, mock_sbd_config, mock_config_exists):
        mock_config_exists.return_value = True
        mock_sbd_config.return_value = outdent("""
            SBD_WATCHDOG=/dev/watchdog
            SBD_WATCHDOG_TIMEOUT=10
        """)
        self.assertEqual([], lib_sbd.get_local_sbd_device_list())
        mock_config_exists.assert_called_once_with(settings.sbd_config)
        mock_sbd_config.assert_called_once_with()

    def test_no_device(self, mock_sbd_config, mock_config_exists):
        mock_config_exists.return_value = True
        mock_sbd_config.return_value = outdent("""
            SBD_WATCHDOG=/dev/watchdog
            SBD_WATCHDOG_TIMEOUT=10
            SBD_DEVICE=""
        """)
        self.assertEqual([], lib_sbd.get_local_sbd_device_list())
        mock_config_exists.assert_called_once_with(settings.sbd_config)
        mock_sbd_config.assert_called_once_with()

    def test_one_device(self, mock_sbd_config, mock_config_exists):
        mock_config_exists.return_value = True
        mock_sbd_config.return_value = outdent("""
            SBD_WATCHDOG=/dev/watchdog
            SBD_WATCHDOG_TIMEOUT=10
            SBD_DEVICE="/dev/vda"
        """)
        self.assertEqual(
            ["/dev/vda"], lib_sbd.get_local_sbd_device_list()
        )
        mock_config_exists.assert_called_once_with(settings.sbd_config)
        mock_sbd_config.assert_called_once_with()

    def test_multiple_devices(self, mock_sbd_config, mock_config_exists):
        mock_config_exists.return_value = True
        mock_sbd_config.return_value = outdent("""
            SBD_WATCHDOG=/dev/watchdog
            SBD_WATCHDOG_TIMEOUT=10
            SBD_DEVICE="/dev/vda;/dev/sda"
        """)
        self.assertEqual(
            ["/dev/vda", "/dev/sda"], lib_sbd.get_local_sbd_device_list()
        )
        mock_config_exists.assert_called_once_with(settings.sbd_config)
        mock_sbd_config.assert_called_once_with()

    def test_config_does_not_exist(self, mock_sbd_config, mock_config_exists):
        mock_config_exists.return_value = False
        self.assertEqual([], lib_sbd.get_local_sbd_device_list())
        mock_config_exists.assert_called_once_with(settings.sbd_config)
        self.assertEqual(0, mock_sbd_config.call_count)

    def test_config_read_error(self, mock_sbd_config, mock_config_exists):
        mock_config_exists.return_value = True
        node = "local node"
        error = "error string"
        mock_sbd_config.side_effect = LibraryError(
            reports.unable_to_get_sbd_config(node, error)
        )
        assert_raise_library_error(
            lib_sbd.get_local_sbd_device_list,
            (
                Severities.ERROR,
                report_codes.UNABLE_TO_GET_SBD_CONFIG,
                {
                    "node": node,
                    "reason": error,
                }
            )
        )
        mock_config_exists.assert_called_once_with(settings.sbd_config)
        mock_sbd_config.assert_called_once_with()


@mock.patch("pcs.lib.sbd.get_local_sbd_device_list")
class IsDeviceSetLocalTest(TestCase):
    def test_no_device(self, mock_device_list):
        mock_device_list.return_value = []
        self.assertFalse(lib_sbd.is_device_set_local())
        mock_device_list.assert_called_once_with()

    def test_one_device(self, mock_device_list):
        mock_device_list.return_value = ["device1"]
        self.assertTrue(lib_sbd.is_device_set_local())
        mock_device_list.assert_called_once_with()

    def test_multiple_devices(self, mock_device_list):
        mock_device_list.return_value = ["device1", "device2"]
        self.assertTrue(lib_sbd.is_device_set_local())
        mock_device_list.assert_called_once_with()


class GetDeviceMessagesInfoTest(TestCase):
    def setUp(self):
        self.mock_runner = mock.MagicMock(spec_set=CommandRunner)

    def test_success(self):
        output = "out"
        device = "device"
        self.mock_runner.run.return_value = output, "", 0
        self.assertEqual(
            output, lib_sbd.get_device_messages_info(self.mock_runner, device)
        )
        self.mock_runner.run.assert_called_once_with(
            [settings.sbd_binary, "-d", device, "list"]
        )

    def test_failed(self):
        output = "out"
        device = "device"
        self.mock_runner.run.return_value = output, "", 1
        assert_raise_library_error(
            lambda: lib_sbd.get_device_messages_info(self.mock_runner, device),
            (
                Severities.ERROR,
                report_codes.SBD_DEVICE_LIST_ERROR,
                {
                    "device": device,
                    "reason": output,
                }
            )
        )
        self.mock_runner.run.assert_called_once_with(
            [settings.sbd_binary, "-d", device, "list"]
        )


class GetDeviceSbdHeaderDumpTest(TestCase):
    def setUp(self):
        self.mock_runner = mock.MagicMock(spec_set=CommandRunner)

    def test_success(self):
        output = "out"
        device = "device"
        self.mock_runner.run.return_value = output, "", 0
        self.assertEqual(
            output, lib_sbd.get_device_sbd_header_dump(self.mock_runner, device)
        )
        self.mock_runner.run.assert_called_once_with(
            [settings.sbd_binary, "-d", device, "dump"]
        )

    def test_failed(self):
        output = "out"
        device = "device"
        self.mock_runner.run.return_value = output, "", 1
        assert_raise_library_error(
            lambda: lib_sbd.get_device_sbd_header_dump(self.mock_runner, device),
            (
                Severities.ERROR,
                report_codes.SBD_DEVICE_DUMP_ERROR,
                {
                    "device": device,
                    "reason": output,
                }
            )
        )
        self.mock_runner.run.assert_called_once_with(
            [settings.sbd_binary, "-d", device, "dump"]
        )


class SetMessageTest(TestCase):
    def setUp(self):
        self.mock_runner = mock.MagicMock(spec_set=CommandRunner)

    def test_success(self):
        self.mock_runner.run.return_value = "", "", 0
        lib_sbd.set_message(self.mock_runner, "device", "node", "test")
        self.mock_runner.run.assert_called_once_with([
            settings.sbd_binary, "-d", "device", "message", "node", "test"
        ])

    def test_failure(self):
        error = "error"
        self.mock_runner.run.return_value = "", error, 1
        assert_raise_library_error(
            lambda: lib_sbd.set_message(
                self.mock_runner, "device", "node", "test"
            ),
            (
                Severities.ERROR,
                report_codes.SBD_DEVICE_MESSAGE_ERROR,
                {
                    "device": "device",
                    "node": "node",
                    "message": "test",
                    "reason": error,
                }
            )
        )
        self.mock_runner.run.assert_called_once_with([
            settings.sbd_binary, "-d", "device", "message", "node", "test"
        ])
