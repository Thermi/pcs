from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

from unittest import TestCase

from pcs.test.library_test_tools import LibraryAssertionMixin
from pcs.test.tools.resources import get_test_resource as rc

import pcs.lib.error_codes as error_codes
from pcs.lib.errors import ReportItemSeverity as severity

import pcs.lib.corosync.config_facade as lib


class FromStringTest(TestCase, LibraryAssertionMixin):
    def test_success(self):
        config = open(rc("corosync.conf")).read()
        facade = lib.ConfigFacade.from_string(config)
        self.assertEqual(facade.__class__, lib.ConfigFacade)
        self.assertEqual(facade.config.export(), config)

    def test_parse_error_missing_brace(self):
        config = "section {"
        self.assert_raise_library_error(
            lambda: lib.ConfigFacade.from_string(config),
            (
                severity.ERROR,
                error_codes.PARSE_ERROR_COROSYNC_CONF_MISSING_CLOSING_BRACE,
                {}
            )
        )

    def test_parse_error_unexpected_brace(self):
        config = "}"
        self.assert_raise_library_error(
            lambda: lib.ConfigFacade.from_string(config),
            (
                severity.ERROR,
                error_codes.PARSE_ERROR_COROSYNC_CONF_UNEXPECTED_CLOSING_BRACE,
                {}
            )
        )


class GetNodesTest(TestCase):
    def assert_equal_nodelist(self, expected_nodes, real_nodelist):
        real_nodes = [
            {"ring0": n.ring0, "ring1": n.ring1, "label": n.label, "id": n.id}
            for n in real_nodelist
        ]
        self.assertEqual(expected_nodes, real_nodes)

    def test_no_nodelist(self):
        config = ""
        facade = lib.ConfigFacade.from_string(config)
        nodes = facade.get_nodes()
        self.assertEqual(0, len(nodes))

    def test_empty_nodelist(self):
        config = """\
nodelist {
}
"""
        facade = lib.ConfigFacade.from_string(config)
        nodes = facade.get_nodes()
        self.assertEqual(0, len(nodes))

    def test_one_nodelist(self):
        config = """\
nodelist {
    node {
        ring0_addr: n1a
        nodeid: 1
    }

    node {
        ring0_addr: n2a
        ring1_addr: n2b
        name: n2n
        nodeid: 2
    }
}
"""
        facade = lib.ConfigFacade.from_string(config)
        nodes = facade.get_nodes()
        self.assertEqual(2, len(nodes))
        self.assert_equal_nodelist(
            [
                {"ring0": "n1a", "ring1": None, "label": "n1a", "id": "1"},
                {"ring0": "n2a", "ring1": "n2b", "label": "n2n", "id": "2"},
            ],
            nodes
        )

    def test_more_nodelists(self):
        config = """\
nodelist {
    node {
        ring0_addr: n1a
        nodeid: 1
    }
}

nodelist {
    node {
        ring0_addr: n2a
        ring1_addr: n2b
        name: n2n
        nodeid: 2
    }
}
"""
        facade = lib.ConfigFacade.from_string(config)
        nodes = facade.get_nodes()
        self.assertEqual(2, len(nodes))
        self.assert_equal_nodelist(
            [
                {"ring0": "n1a", "ring1": None, "label": "n1a", "id": "1"},
                {"ring0": "n2a", "ring1": "n2b", "label": "n2n", "id": "2"},
            ],
            nodes
        )


class GetQuorumOptionsTest(TestCase):
    def test_no_quorum(self):
        config = ""
        facade = lib.ConfigFacade.from_string(config)
        options = facade.get_quorum_options()
        self.assertEqual({}, options)

    def test_empty_quorum(self):
        config = """\
quorum {
}
"""
        facade = lib.ConfigFacade.from_string(config)
        options = facade.get_quorum_options()
        self.assertEqual({}, options)

    def test_no_options(self):
        config = """\
quorum {
    provider: corosync_votequorum
}
"""
        facade = lib.ConfigFacade.from_string(config)
        options = facade.get_quorum_options()
        self.assertEqual({}, options)

    def test_some_options(self):
        config = """\
quorum {
    provider: corosync_votequorum
    wait_for_all: 0
    nonsense: ignored
    auto_tie_breaker: 1
    last_man_standing: 0
    last_man_standing_window: 1000
}
"""
        facade = lib.ConfigFacade.from_string(config)
        options = facade.get_quorum_options()
        self.assertEqual(
            {
                "auto_tie_breaker": "1",
                "last_man_standing": "0",
                "last_man_standing_window": "1000",
                "wait_for_all": "0",
            },
            options
        )

    def test_option_repeated(self):
        config = """\
quorum {
    wait_for_all: 0
    wait_for_all: 1
}
"""
        facade = lib.ConfigFacade.from_string(config)
        options = facade.get_quorum_options()
        self.assertEqual(
            {
                "wait_for_all": "1",
            },
            options
        )

    def test_quorum_repeated(self):
        config = """\
quorum {
    wait_for_all: 0
    last_man_standing: 0
}
quorum {
    last_man_standing_window: 1000
    wait_for_all: 1
}
"""
        facade = lib.ConfigFacade.from_string(config)
        options = facade.get_quorum_options()
        self.assertEqual(
            {
                "last_man_standing": "0",
                "last_man_standing_window": "1000",
                "wait_for_all": "1",
            },
            options
        )


class SetQuorumOptionsTest(TestCase, LibraryAssertionMixin):
    def test_add_missing_section(self):
        config = ""
        facade = lib.ConfigFacade.from_string(config)
        facade.set_quorum_options({"wait_for_all": "0"})
        self.assertEqual(
            """\
quorum {
    wait_for_all: 0
}
""",
            facade.config.export()
        )

    def test_del_missing_section(self):
        config = ""
        facade = lib.ConfigFacade.from_string(config)
        facade.set_quorum_options({"wait_for_all": ""})
        self.assertEqual(
            """\
quorum {
}
""",
            facade.config.export()
        )

    def test_add_all_options(self):
        config = open(rc("corosync.conf")).read()
        facade = lib.ConfigFacade.from_string(config)
        expected_options = {
            "auto_tie_breaker": "1",
            "last_man_standing": "0",
            "last_man_standing_window": "1000",
            "wait_for_all": "0",
        }
        facade.set_quorum_options(expected_options)

        test_facade = lib.ConfigFacade.from_string(facade.config.export())
        self.assertEqual(
            expected_options,
            test_facade.get_quorum_options()
        )

    def test_complex(self):
        config = """\
quorum {
    wait_for_all: 0
    last_man_standing_window: 1000
}
quorum {
    wait_for_all: 0
    last_man_standing: 1
}
"""
        facade = lib.ConfigFacade.from_string(config)
        facade.set_quorum_options({
            "auto_tie_breaker": "1",
            "wait_for_all": "1",
            "last_man_standing_window": "",
        })

        test_facade = lib.ConfigFacade.from_string(facade.config.export())
        self.assertEqual(
            {
                "auto_tie_breaker": "1",
                "last_man_standing": "1",
                "wait_for_all": "1",
            },
            test_facade.get_quorum_options()
        )

    def test_invalid_value_no_effect_on_config(self):
        config= """\
quorum {
    auto_tie_breaker: 1
    wait_for_all: 1
    last_man_standing: 1
}
"""
        facade = lib.ConfigFacade.from_string(config)
        options = {
            "auto_tie_breaker": "",
            "wait_for_all": "nonsense",
            "last_man_standing": "0",
            "last_man_standing_window": "250",
        }
        self.assert_raise_library_error(
            lambda: facade.set_quorum_options(options),
            (
                severity.ERROR,
                error_codes.INVALID_OPTION_VALUE,
                {
                    "option_name": "wait_for_all",
                    "option_value": "nonsense",
                    "allowed_values_raw": ("0", "1"),
                    "allowed_values": "0 or 1",
                }
            )
        )
        self.assertEqual(
            lib.ConfigFacade.from_string(config).get_quorum_options(),
            facade.get_quorum_options()
        )

    def test_invalid_all_values(self):
        config= ""
        facade = lib.ConfigFacade.from_string(config)
        options = {
            "auto_tie_breaker": "atb",
            "last_man_standing": "lms",
            "last_man_standing_window": "lmsw",
            "wait_for_all": "wfa",
        }
        self.assert_raise_library_error(
            lambda: facade.set_quorum_options(options),
            (
                severity.ERROR,
                error_codes.INVALID_OPTION_VALUE,
                {
                    "option_name": "auto_tie_breaker",
                    "option_value": "atb",
                    "allowed_values_raw": ("0", "1"),
                    "allowed_values": "0 or 1",
                }
            ),
            (
                severity.ERROR,
                error_codes.INVALID_OPTION_VALUE,
                {
                    "option_name": "last_man_standing",
                    "option_value": "lms",
                    "allowed_values_raw": ("0", "1"),
                    "allowed_values": "0 or 1",
                }
            ),
            (
                severity.ERROR,
                error_codes.INVALID_OPTION_VALUE,
                {
                    "option_name": "last_man_standing_window",
                    "option_value": "lmsw",
                    "allowed_types_raw": ("integer", ),
                    "allowed_values": "integer",
                }
            ),
            (
                severity.ERROR,
                error_codes.INVALID_OPTION_VALUE,
                {
                    "option_name": "wait_for_all",
                    "option_value": "wfa",
                    "allowed_values_raw": ("0", "1"),
                    "allowed_values": "0 or 1",
                }
            )
        )
        self.assertEqual(
            lib.ConfigFacade.from_string(config).get_quorum_options(),
            facade.get_quorum_options()
        )

    def test_invalid_option(self):
        config= ""
        facade = lib.ConfigFacade.from_string(config)
        options = {
            "auto_tie_breaker": "1",
            "nonsense1": "0",
            "nonsense2": "doesnt matter",
        }
        self.assert_raise_library_error(
            lambda: facade.set_quorum_options(options),
            (
                severity.ERROR,
                error_codes.INVALID_OPTION,
                {
                    "type": "quorum",
                    "option": "nonsense1",
                    "allowed_raw": (
                        "auto_tie_breaker", "last_man_standing",
                        "last_man_standing_window", "wait_for_all"
                    ),
                }
            ),
            (
                severity.ERROR,
                error_codes.INVALID_OPTION,
                {
                    "type": "quorum",
                    "option": "nonsense2",
                    "allowed_raw": (
                        "auto_tie_breaker", "last_man_standing",
                        "last_man_standing_window", "wait_for_all"
                    ),
                }
            )
        )
        self.assertEqual(
            lib.ConfigFacade.from_string(config).get_quorum_options(),
            facade.get_quorum_options()
        )