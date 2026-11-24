import unittest
from unittest.mock import MagicMock, Mock

from configshell.node import ConfigNode

from targetcli.ui_backstore import UIBackstore


def make_node(name, parent):
    node = ConfigNode(name, parent)
    node.refresh = Mock()
    return node


def make_lun(fabric, wwn, tag, multi_tpg):
    target = Mock(wwn=wwn)
    target.fabric_module.name = fabric
    target.has_feature.side_effect = lambda feature: multi_tpg and feature == 'tpgts'
    return Mock(parent_tpg=Mock(parent_target=target, tag=tag))


class BackstoreDeleteTest(unittest.TestCase):
    '''
    Deleting a storage object deletes its LUNs and their mapped LUNs, so the
    UI nodes of the TPGs that used it must be refreshed.

    Cached tree:
        /loopback/naa.single         single-TPG target (merged with its TPG)
        /iscsi/iqn.multi/tpg1        multi-TPG target
        /backstores/fileio/disk1     the storage object to delete
    '''

    def setUp(self):
        self.root = ConfigNode('/', shell=MagicMock())
        self.root.refresh = Mock()
        self.loopback = make_node('loopback', self.root)
        self.single = make_node('naa.single', self.loopback)
        self.iscsi = make_node('iscsi', self.root)
        self.multi = make_node('iqn.multi', self.iscsi)
        self.tpg1 = make_node('tpg1', self.multi)

        backstores = make_node('backstores', self.root)
        self.backstore = UIBackstore.__new__(UIBackstore)
        ConfigNode.__init__(self.backstore, 'fileio', backstores)
        self.storage = make_node('disk1', self.backstore)
        self.storage.rtsnode = Mock()

        self.all_nodes = [self.root, self.loopback, self.single,
                          self.iscsi, self.multi, self.tpg1]

    def delete(self, *luns):
        self.storage.rtsnode.attached_luns = list(luns)
        self.backstore.ui_command_delete('disk1')

    def refreshed(self):
        return [node for node in self.all_nodes if node.refresh.called]

    def test_refreshes_each_tpg_once(self):
        self.delete(make_lun('loopback', 'naa.single', 1, False),
                    make_lun('iscsi', 'iqn.multi', 1, True),
                    make_lun('iscsi', 'iqn.multi', 1, True))
        self.assertEqual(self.refreshed(), [self.single, self.tpg1])
        self.tpg1.refresh.assert_called_once_with()
        self.storage.rtsnode.delete.assert_called_once_with(save=False)
        self.assertNotIn(self.storage, self.backstore.children)

    def test_uncached_tpgs_are_skipped(self):
        self.delete(make_lun('vhost', 'naa.x', 1, True),           # no fabric
                    make_lun('loopback', 'naa.other', 1, False),   # no target
                    make_lun('iscsi', 'iqn.multi', 2, True))       # no TPG
        self.assertEqual(self.refreshed(), [])
        self.assertNotIn(self.storage, self.backstore.children)

    def test_no_attached_luns(self):
        self.delete()
        self.assertEqual(self.refreshed(), [])
        self.assertNotIn(self.storage, self.backstore.children)

    def test_refreshes_even_if_delete_fails(self):
        self.storage.rtsnode.delete.side_effect = OSError("busy")
        with self.assertRaises(OSError):
            self.delete(make_lun('loopback', 'naa.single', 1, False))
        self.assertEqual(self.refreshed(), [self.single])
        self.assertIn(self.storage, self.backstore.children)


if __name__ == '__main__':
    unittest.main()
