from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

from pcs.common import report_codes
from pcs.lib import reports
from pcs.lib.errors import ReportItem, LibraryError
from pcs.lib.external import (
    NodeCommunicationException,
    node_communicator_exception_to_report_item,
)
from pcs.lib.corosync import live as corosync_live


def distribute_corosync_conf(lib_env, node_addr_list, config_text):
    """
    Send corosync.conf to several cluster nodes and reload corosync config
    node_addr_list nodes to send config to (NodeAddressesList instance)
    config_text text of corosync.conf
    """
    lib_env.report_processor.process(
        reports.corosync_config_distribution_started()
    )
    report = []
    # TODO use parallel communication
    for node in node_addr_list:
        try:
            corosync_live.set_remote_corosync_conf(
                lib_env.node_communicator(),
                node,
                config_text
            )
            lib_env.report_processor.process(
                reports.corosync_config_accepted_by_node(node.label)
            )
        except NodeCommunicationException as e:
            report.append(node_communicator_exception_to_report_item(e))
            report.append(ReportItem.error(
                report_codes.NODE_COROSYNC_CONF_SAVE_ERROR,
                "{node}: Unable to set corosync config",
                info={"node": node.label}
            ))
    if report:
        raise LibraryError(*report)

    corosync_live.reload_config(lib_env.cmd_runner())
    lib_env.report_processor.process(reports.corosync_config_reloaded())
