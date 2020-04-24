 [[inputs.snmp]]
   agents = ["{{ host }}:161"]
   timeout = "2s"
   interval = "5m"
   retries = 1
   version = 3
   max_repetitions = 10
   sec_name = "ipointernal"
   sec_level = "authPriv"
   context_name = ""
   auth_protocol = "SHA"
   auth_password = "Aixue3MiYohp"
   priv_protocol = "AES"
   priv_password = "iL7kie3eiJah"
   name = "{{ hostname }}"
   [[inputs.snmp.field]]
    name = "hostname"
    oid = ".1.3.6.1.2.1.1.5.0"
    is_tag = true
   [[inputs.snmp.table]]
    name = "interface_address"
    inherit_tags = [ "hostname" ]
    index_as_tag = true
   [[inputs.snmp.table.field]]
    name = "Ifindex"
    oid = ".1.3.6.1.2.1.4.20.1.2"
