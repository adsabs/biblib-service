# Some const. variables
$path_var = "/usr/bin:/usr/sbin:/bin:/usr/local/sbin:/usr/sbin:/sbin"
$build_packages = ['python', 'python-dev', 'python-pip', 'libpq-dev', 'postgresql', 'graphviz']
$pip_requirements = "/vagrant/requirements.txt"

# Update package list
exec {'apt_update_1':
	command => 'apt-get update && touch /etc/.apt-updated-by-puppet1',
	creates => '/etc/.apt-updated-by-puppet1',
	path => $path_var,
}

# Install packages
package {$build_packages:
	ensure => installed,
	require => Exec['apt_update_1'],
}

# Upgrade pip otherwise will not work properly
exec {'distribute_upgrade':
    command => "easy_install -U distribute",
    logoutput => on_failure,
    path => $path_var,
    require => Package['python', 'python-pip', 'python-dev'],
}

# Install all python dependencies for selenium and general software
exec {'pip_install_modules':
    command => "pip install -r ${pip_requirements}",
    logoutput => on_failure,
    path => $path_var,
    tries => 2,
    timeout => 1000, # This is only require for Scipy/Matplotlib - they take a while
    require => Package[$build_packages],
}

Exec['apt_update_1'] -> Package[$build_packages] -> Exec['distribute_upgrade'] -> Exec['pip_install_modules']