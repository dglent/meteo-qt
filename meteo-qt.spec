%define aname meteo_qt
Name:           meteo-qt
Version:        0.1.0
Release:        %mkrel 1
Group:          Graphical desktop/Other
Summary:        Weather status system tray application
License:        GPLv3
URL:            https://github.com/dglent/meteo-qt
Source0:        %{name}-%{version}.tar.gz
BuildArch:      noarch
BuildRequires:  pkgconfig(QtCore)
BuildRequires:  python-qt4-devel
BuildRequires:  python3
BuildRequires:  imagemagick
Requires:       python3-qt4
Requires:       python3-sip
Requires:       python3-urllib3
Requires:       python3-lxml

%description
A Qt system tray application for the weather status

%prep
%setup -q

%build
%__python3 setup.py build

%install
%__python3 ./setup.py install --skip-build --root=%{buildroot}
%__mkdir -p %{buildroot}%{_iconsdir}/hicolor/{16x16,32x32}/apps
convert -scale 16x16 meteo_qt/images/meteo-qt.png %{buildroot}%{_iconsdir}/hicolor/16x16/apps/meteo-qt.png
convert -scale 32x32 meteo_qt/images/meteo-qt.png %{buildroot}%{_iconsdir}/hicolor/32x32/apps/meteo-qt.png

%files -f %{name}.lang
%doc TODO CHANGELOG README.md
%{_datadir}/%{aname}/images/
%{_bindir}/%{name}
%{_iconsdir}/%{name}.png
%{python3_sitelib}/%{aname}-%{version}-py%py3ver.egg-info
%{python3_sitelib}/%{aname}/
%{_datadir}/applications/%{name}.desktop
%{_iconsdir}/hicolor/*/apps/meteo-qt.png
