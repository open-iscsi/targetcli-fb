Name:           targetcli
Version:        2.2.0
Release:        1
Summary:        A command shell for managing the Linux LIO kernel target

License:        Apache-2.0
URL:            http://github.com/open-iscsi/targetcli-fb
Source:         %{pypi_source targetcli}

BuildArch:      noarch
BuildRequires:  python3-devel
BuildRequires:  python3-rtslib
BuildRequires:  python3-configshell
Requires:       target-restore
Requires:       python3-gobject-base
Requires:       python3-dbus

%global _description %{expand:
An administration shell for configuring iSCSI, FCoE, and other
SCSI targets, using the TCM/LIO kernel target subsystem. FCoE
users will also need to install and use fcoe-utils.}


%description -n targetcli %_description


%prep
%autosetup -p1 -n targetcli-%{version}


%generate_buildrequires
%pyproject_buildrequires

%build
%pyproject_wheel


%install
%pyproject_install
%pyproject_save_files targetcli

mkdir -p %{buildroot}%{_sysconfdir}/target/backup
mkdir -p %{buildroot}%{_mandir}/man8/
install -m 644 targetcli*.8 %{buildroot}%{_mandir}/man8/
mkdir -p %{buildroot}%{_unitdir}/
install -m 644 systemd/* %{buildroot}%{_unitdir}/

%check
%pyproject_check_import


%files -n targetcli -f %{pyproject_files}
%doc README.md
%license COPYING
%{_bindir}/targetcli
%{_bindir}/targetclid
%{_mandir}/man8/targetcli*.8*
%{_unitdir}/targetclid.*
%dir %{_sysconfdir}/target
%dir %{_sysconfdir}/target/backup


%changelog
%autochangelog
