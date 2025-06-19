Name:           python-targetcli-fb
Version:        {{{ version }}}
Release:        1%{?dist}
Summary:        Command shell for managing the Linux LIO kernel target

License:        Apache-2.0
URL:            https://github.com/open-iscsi/targetcli-fb
Source:         %{pypi_source targetcli}

BuildArch:      noarch
BuildRequires:  python3-devel
BuildRequires:  python3-setuptools
BuildRequires:  python3-hatchling
BuildRequires:  python3-hatch-vcs
BuildRequires:  python3-pytest
BuildRequires:  python3-pytest-cov
BuildRequires:  python3-pytest-mock

# Runtime dependencies from pyproject.toml
Requires:       python3-gobject
Requires:       python3-configshell-fb
Requires:       python3-rtslib-fb
Requires:       python3-six
Requires:       python3-dbus

%description
An administration shell for configuring iSCSI, FCoE, and other SCSI targets,
using the TCM/LIO kernel target subsystem.

%package -n python3-targetcli-fb
Summary:        %{summary}
Requires:       python3-configshell-fb
Requires:       python3-rtslib-fb
Requires:       python3-gobject
%{?python_provide:%python_provide python3-targetcli-fb}

%description -n python3-targetcli-fb
An administration shell for configuring iSCSI, FCoE, and other SCSI targets,
using the TCM/LIO kernel target subsystem.

%prep
%autosetup -n targetcli-%{version}

%build
%pyproject_wheel

%install
%pyproject_install
%pyproject_save_files targetcli

# Install systemd files
install -d %{buildroot}%{_unitdir}
install -p -m 644 systemd/targetclid.service %{buildroot}%{_unitdir}/
install -p -m 644 systemd/targetclid.socket %{buildroot}%{_unitdir}/

# Install man pages
install -d %{buildroot}%{_mandir}/man8
install -p -m 644 targetcli.8 %{buildroot}%{_mandir}/man8/
install -p -m 644 targetclid.8 %{buildroot}%{_mandir}/man8/

%files -n python3-targetcli-fb -f %{pyproject_files}
%license COPYING
%doc README.md THANKS
%{_bindir}/targetcli
%{_bindir}/targetclid
%{_mandir}/man8/targetcli.8*
%{_mandir}/man8/targetclid.8*
%{_unitdir}/targetclid.service
%{_unitdir}/targetclid.socket

%changelog
%autochangelog
