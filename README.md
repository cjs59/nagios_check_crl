### Nagios plugin to check CRL expiry in minutes

This is a nagios plugin which you can use to check if a CRL (Certificate Revocation List, public list with revoked certificates) is still valid.

Forked from [Remy van Elst](https://github.com/RaymiiOrg/nagios)'s check_crl.


#### Installation

This guide covers the steps needed for Debian 12. It should also work on other distros, but make sure to modify the commands where needed.

Make sure you have openssl, python3 and a module needed by the script installed on the nagios host:

    apt-get install python3 openssl python-m2crypto

Now checkout the script on the host. I've placed in */opt/nagios_check_crl/* - create this with appropriate permissions first.

    git clone https://github.com/cjs59/nagios_check_crl.git /opt/nagios_check_crl

Now test the script. I'm using the URL of the LetsEncrypt root CA CRL.

    /opt/nagios_check_crl/check_crl.py -u http://x1.c.lencr.org/ -w 480 -c 360
    CRL OK - http://x1.c.lencr.org/ expires in 113 days (on Mon Nov 10 23:59:59 2025 GMT)

    /opt/nagios_check_crl/check_crl.py -u http://x1.c.lencr.org/ -w 432000 -c 360
    CRL WARNING - http://x1.c.lencr.org/ expires in 113 days (on Mon Nov 10 23:59:59 2025 GMT)

    /opt/nagios_check_crl/check_crl.py -u http://x1.c.lencr.org/ -w 432000 -c 432000
    CRL CRITICAL - http://x1.c.lencr.org/ expires in 113 days (on Mon Nov 10 23:59:59 2025 GMT)


#### Usage

Lets add the nagios command:

    define command {
        command_name            check_crl
        command_line            /opt/nagios_check_crl/check_crl.py -u $ARG1$ -w $ARG2$ -c $ARG3$
    }

And lets add the command to a service check:

    define service {
        use                     generic-service
        host_name               localhost
        service_description     Lets Encrypt root CRL
        contacts                nagiosadmin
        check_command           check_crl!http://x1.c.lencr.org/!480!360
    }

The above service check runs on the nagios defined host "localhost", uses the (default) service template "generic-service" and had the contact "nagiosadmin". As you can see, the URL maps to $ARG1$, the warning hours to $ARG2$ and the critical hours to $ARG3$. This means that if the field *"Next Update:"* is less then 8 hours in the future you get a warning and if it is less then 6 hours you get a critical.

Alternatively, store the service configuration in a file, which makes it easier when generating the Nagios configuration from an IP registration database.

    define command {
        command_name            check_crl
        command_line            /opt/nagios_check_crl/check_crl.py @'/etc/nagios4/crl/$HOSTNAME$.ini'
    }

    define service {
        use                     generic-service
        hostgroup_name          crl-servers
        service_description     CRL
        contacts                nagiosadmin
        check_command           check_crl
    }

    define hostgroup {
        hostgroup_name          crl-servers
        alias                   CRL Servers
        members                 root-ca-server,intermediate-ca-server
    }

/etc/nagios4/crl/root-ca-server.ini contains:

    --url http://root-ca-server.domain/crl
    --warning 86400
    --critical 43200

/etc/nagios4/crl/intermediate-ca-server.ini contains:

    --url http://intermediate-ca-server.domain/crl
    --warning 480
    --critical 360

