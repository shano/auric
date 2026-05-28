Name:           auric
Version:        0.1.0
Release:        1%{?dist}
Summary:        Linux/GNOME AI tool usage tracker
License:        MIT
URL:            https://github.com/shano/auric
Source0:        auric-%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  python3-devel
BuildRequires:  pyproject-rpm-macros

Requires:       python3-gobject
Requires:       python3dist(httpx) >= 0.27
Requires:       python3dist(tomli-w) >= 1.0
Requires:       gtk3

%description
System tray application for Linux/GNOME that monitors Claude Code token usage,
rate limits, and costs live. Polls ~/.claude/stats-cache.json for historical
usage and pings the Anthropic API to harvest live rate limit state from
response headers.

%prep
%autosetup -n auric-%{version}

%generate_buildrequires
%pyproject_buildrequires

%build
%pyproject_wheel

%install
%pyproject_install
%pyproject_save_files -l auric

%files -f %{pyproject_files}
%{_bindir}/auric

%changelog
