# This file is part of RTSAdmin Community Edition.
# Copyright (c) 2011 by RisingTide Systems LLC
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, version 3 (AGPLv3).
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

NAME = rtsadmin
LIB = /usr/share
DOC = ${LIB}/doc/
SETUP = ./setup.py
CLEAN = ./bin/clean
GENDOC = ./bin/gendoc

all: usage
usage:
	@echo "Usage:"
	@echo "  make clean       - Cleanup the local repository"
	@echo "  make packages    - Generate the Debian and RPM packages"
	@echo
	@echo "Developer targets:"
	@echo "  make doc         - Generate the documentation"
	@echo "  make sdist       - Build the source tarball"
	@echo "  make bdist       - Build the installable tarball"
	@echo "  make install     - Install rtsadmin"
	@echo "  make installdocs - Install the documentation"

install:
	${SETUP} install

doc:
	${GENDOC}

installdocs: doc
	@test -e ${DOC} || \
	    echo "Could not find ${DOC}; check the makefile variables."
	@test -e ${DOC}
	cp -r doc/* ${DOC}/${NAME}/

clean:
	${CLEAN}
	./bin/gen_changelog_cleanup

packages: clean doc
	./bin/gen_changelog
	dpkg-buildpackage -rfakeroot | tee dpkg-buildpackage.log
	head -1 debian/changelog  | awk '{print $$2}' | tr -d "()\n" > dpkg-buildpackage.version
	./bin/gen_changelog_cleanup
	@test -e dist || mkdir dist
	mv ../${NAME}_$$(cat dpkg-buildpackage.version).dsc dist
	mv ../${NAME}_$$(cat dpkg-buildpackage.version)_*.changes dist
	mv ../${NAME}_$$(cat dpkg-buildpackage.version).tar.gz dist
	mv ../*${NAME}*$$(cat dpkg-buildpackage.version)*.deb dist
	@test -e build || mkdir build
	cd build; alien --scripts -k -g -r ../dist/rtsadmin-doc_$$(cat ../dpkg-buildpackage.version)_all.deb
	cd build/rtsadmin-doc-*; mkdir usr/share/doc/packages
	cd build/rtsadmin-doc-*; mv usr/share/doc/rtsadmin-doc usr/share/doc/packages/
	cd build/rtsadmin-doc-*; perl -pi -e "s,/usr/share/doc/rtsadmin-doc,/usr/share/doc/packages/rtsadmin-doc,g" *.spec
	cd build/rtsadmin-doc-*; perl -pi -e "s,%%{ARCH},noarch,g" *.spec
	cd build/rtsadmin-doc-*; perl -pi -e "s,%post,%posttrans,g" *.spec
	cd build/rtsadmin-doc-*; rpmbuild --buildroot $$PWD -bb *.spec
	cd build; alien --scripts -k -g -r ../dist/rtsadmin_$$(cat ../dpkg-buildpackage.version)_all.deb; cd ..
	cd build/rtsadmin*; mkdir usr/share/doc/packages
	cd build/rtsadmin*; mv usr/share/doc/rtsadmin usr/share/doc/packages/
	cd build/rtsadmin*; perl -pi -e "s,/usr/share/doc/rtsadmin,/usr/share/doc/packages/rtsadmin,g" *.spec
	cd build/rtsadmin*; perl -pi -e 's/Group:/Requires: python >= 2.5, python-rtslib\nConflicts: rtsadmin-frozen\nGroup:/g' *.spec
	cd build/rtsadmin*; perl -pi -e "s,%%{ARCH},noarch,g" *.spec
	cd build/rtsadmin*; perl -pi -e "s,%post,%posttrans,g" *.spec
	cd build/rtsadmin*; rpmbuild --buildroot $$PWD -bb *.spec
	rm -rf build/rtsadmin*$$(cat dpkg-buildpackage.version)
	mv build/*.rpm dist
	rm dpkg-buildpackage.log dpkg-buildpackage.version

sdist: clean doc
	${SETUP} sdist

bdist: clean doc
	${SETUP} bdist

