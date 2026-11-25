import unittest
from unittest.mock import MagicMock, Mock

from configshell.node import ConfigNode

from targetcli.ui_backstore import UIBackstore
from targetcli.ui_target import UITPG


def make_node(name, parent, cls=ConfigNode):
    # Bypass the UI classes' constructors, which read configFS
    node = cls.__new__(cls)
    ConfigNode.__init__(node, name, parent)
    node.refresh = Mock()
    return node


def make_tpg(name, parent, n_luns):
    tpg = make_node(name, parent, UITPG)
    luns = make_node('luns', tpg)
    for i in range(n_luns):
        make_node(f'lun{i}', luns).rtsnode = Mock(exists=True)
    return tpg


class BackstoreDeleteTest(unittest.TestCase):
    '''
    Deleting a storage object deletes its LUNs and their mapped LUNs, so the
    cached UI nodes of the TPGs that had those LUNs must be refreshed.

    Cached tree:
        /loopback/naa.single              single-TPG target (merged with its TPG)
        /iscsi/iqn.multi/tpg1, tpg2       multi-TPG target
        /backstores/fileio/disk1          the storage object to delete
    '''

    def setUp(self):
        self.root = ConfigNode('/', shell=MagicMock())
        self.single = make_tpg('naa.single', make_node('loopback', self.root), 1)
        multi = make_node('iqn.multi', make_node('iscsi', self.root))
        self.tpg1 = make_tpg('tpg1', multi, 1)
        self.tpg2 = make_tpg('tpg2', multi, 2)

        self.backstore = make_node('fileio', make_node('backstores', self.root), UIBackstore)
        self.storage = make_node('disk1', self.backstore)
        self.storage.rtsnode = Mock()

    def delete(self, *luns):
        '''Runs the delete command, with rtslib deleting the given LUNs.'''
        def rts_delete(**_):
            for lun in luns:
                lun.rtsnode.exists = False

        if not self.storage.rtsnode.delete.side_effect:
            self.storage.rtsnode.delete.side_effect = rts_delete
        self.backstore.ui_command_delete('disk1')

    def lun(self, tpg, index):
        return tpg.get_child('luns').get_child(f'lun{index}')

    def refreshed(self):
        tpgs = [self.single, self.tpg1, self.tpg2]
        return [tpg for tpg in tpgs if tpg.refresh.called]

    def test_refreshes_tpgs_that_lost_a_lun(self):
        self.delete(self.lun(self.single, 0), self.lun(self.tpg2, 0), self.lun(self.tpg2, 1))
        self.assertEqual(self.refreshed(), [self.single, self.tpg2])
        self.tpg2.refresh.assert_called_once_with()
        self.storage.rtsnode.delete.assert_called_once_with(save=False)
        self.assertNotIn(self.storage, self.backstore.children)

    def test_unused_storage_object_refreshes_nothing(self):
        self.delete()
        self.assertEqual(self.refreshed(), [])
        self.assertNotIn(self.storage, self.backstore.children)

    def test_refreshes_even_if_delete_fails(self):
        lun = self.lun(self.tpg1, 0)

        def rts_delete(**_):
            lun.rtsnode.exists = False
            raise OSError("busy")

        self.storage.rtsnode.delete.side_effect = rts_delete
        with self.assertRaises(OSError):
            self.delete()
        self.assertEqual(self.refreshed(), [self.tpg1])
        self.assertIn(self.storage, self.backstore.children)


if __name__ == '__main__':
    unittest.main()
