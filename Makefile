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
GENDOC = ./bin/gendoc
RPMVERSION = $$(grep Version: redhat/rtsadmin.spec | awk '{print $$2}')

all: usage
usage:
	@echo "Usage:"
	@echo "  make deb         - Builds debian packages."
	@echo "  make rpm         - Builds redhat packages."
	@echo "  make clean       - Cleanup the local repository"
	@echo "  make cleanall    - Cleanup the local repository and packages"
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
	rm -fv rtsadmin/*.pyc rtsadmin/*.html
	rm -frv doc
	rm -frv rtsadmin.egg-info MANIFEST build
	rm -frv pdf html
	rm -frv debian/tmp
	rm -fv build-stamp
	rm -fv dpkg-buildpackage.log dpkg-buildpackage.version
	rm -frv *.rpm warnrtsadmin.txt buildrtsadmin
	rm -fv debian/*.debhelper.log debian/*.debhelper debian/*.substvars debian/files
	rm -fvr debian/rtsadmin-python2.5/
	rm -fvr debian/rtsadmin-python2.6/ debian/rtsadmin/ debian/rtsadmin-doc/
	rm -fv redhat/*.spec *.spec redhat/sed* sed*
	rm -frv rtsadmin-*
	./bin/gen_changelog_cleanup
	@echo "Finished cleanup."

cleanall: clean
	rm -frv dist

deb: doc
	./bin/gen_changelog
	dpkg-buildpackage -rfakeroot | tee dpkg-buildpackage.log
	./bin/gen_changelog_cleanup
	grep "source version" dpkg-buildpackage.log | awk '{print $$4}' > dpkg-buildpackage.version
	@test -e dist || mkdir dist
	mv ../${NAME}_$$(cat dpkg-buildpackage.version).dsc dist
	mv ../${NAME}_$$(cat dpkg-buildpackage.version)_*.changes dist
	mv ../${NAME}_$$(cat dpkg-buildpackage.version).tar.gz dist
	mv ../*${NAME}*$$(cat dpkg-buildpackage.version)*.deb dist
	./bin/gen_changelog_cleanup

rpm: doc
	./bin/gen_changelog
	@echo Building RPM version ${RPMVERSION}
	mkdir -p ~/rpmbuild/SOURCES/
	mkdir -p build
	git archive master --prefix rtsadmin/ > build/rtsadmin.tar
	cd build; tar mxf rtsadmin.tar; rm rtsadmin.tar
	cp rtsadmin/__init__.py build/rtsadmin/rtsadmin
	cp -r doc build/rtsadmin/
	mv build/rtsadmin rtsadmin-${RPMVERSION}
	tar zcf ~/rpmbuild/SOURCES/rtsadmin-${RPMVERSION}.tar.gz rtsadmin-${RPMVERSION}
	rm -fr rtsadmin-${RPMVERSION}
	rpmbuild -ba redhat/*.spec
	@test -e dist || mkdir dist
	mv ~/rpmbuild/SRPMS/rtsadmin-${RPMVERSION}*.src.rpm dist/
	mv ~/rpmbuild/RPMS/*/rtsadmin-${RPMVERSION}*.rpm dist/
	mv ~/rpmbuild/RPMS/noarch/rtsadmin-doc-${RPMVERSION}*.rpm dist/
	./bin/gen_changelog_cleanup

sdist: clean doc
	${SETUP} sdist

bdist: clean doc
	${SETUP} bdist

