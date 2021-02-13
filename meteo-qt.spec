%define aname meteo_qt

Name:           meteo-qt
Version:        2.2
Release:        %mkrel 1
Group:          Graphical desktop/Other
Summary:        Weather status system tray application
License:        GPLv3
URL:            https://github.com/dglent/meteo-qt
Source0:        %{name}-%{version}.tar.gz
BuildArch:      noarch
BuildRequires:  python3-qt5-devel
BuildRequires:  qttools5
Requires:       python3-qt5
Requires:       python3-sip
Requires:       python3-urllib3
Requires:       python3-lxml
Recommends:     qttranslations5

%description
A Qt system tray application for the weather status
Weather data from: http://openweathermap.org/

%prep
%setup -q

%build
%py3_build

%install
%py3_install

%files
%doc TODO CHANGELOG README.md
%exclude %_defaultdocdir/%{name}/LICENSE
%{_bindir}/%{name}
%{_iconsdir}/weather-few-clouds.png
%{python3_sitelib}/%{aname}-%{version}-py%python3_version.egg-info
%{python3_sitelib}/%{aname}/
%{_datadir}/applications/%{name}.desktop
%{_datadir}/meteo_qt/translations/
