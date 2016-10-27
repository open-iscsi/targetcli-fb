PKGNAME = targetcli-fb
NAME = targetcli
GIT_BRANCH = $$(git branch | grep \* | tr -d \*)
VERSION = $$(basename $$(git describe --tags | tr - . | sed 's/^v//'))

all:
	@echo "Usage:"
	@echo
	@echo "  make release     - Generates the release tarball."
	@echo
	@echo "  make clean       - Cleanup the local repository build files."
	@echo "  make cleanall    - Also remove dist/*"

clean:
	@rm -fv ${NAME}/*.pyc ${NAME}/*.html
	@rm -frv doc
	@rm -frv ${NAME}.egg-info MANIFEST build
	@rm -frv results
	@rm -frv ${NAME}-*
	@rm -frv log/
	@echo "Finished cleanup."

cleanall: clean
	@rm -frv dist

release: build/release-stamp
build/release-stamp:
	@mkdir -p build
	@echo "Exporting the repository files..."
	@git archive ${GIT_BRANCH} --prefix ${PKGNAME}-${VERSION}/ \
		| (cd build; tar xfp -)
	@echo "Cleaning up the target tree..."
	@rm -f build/${PKGNAME}-${VERSION}/Makefile
	@rm -f build/${PKGNAME}-${VERSION}/.gitignore
	@rm -rf build/${PKGNAME}-${VERSION}/bin
	@echo "Fixing version string..."
	@sed -i "s/__version__ = .*/__version__ = '${VERSION}'/g" \
		build/${PKGNAME}-${VERSION}/${NAME}/__init__.py
	@find build/${PKGNAME}-${VERSION}/ -exec \
		touch -t $$(date -d @$$(git show -s --format="format:%at") \
			+"%Y%m%d%H%M.%S") {} \;
	@mkdir -p dist
	@cd build; tar -c --owner=0 --group=0 --numeric-owner \
		--format=gnu -b20 --quoting-style=escape \
		-f ../dist/${PKGNAME}-${VERSION}.tar \
		$$(find ${PKGNAME}-${VERSION} -type f | sort)
	@gzip -6 -n dist/${PKGNAME}-${VERSION}.tar
	@echo "Generated release tarball:"
	@echo "    $$(ls dist/${PKGNAME}-${VERSION}.tar.gz)"
	@touch build/release-stamp
