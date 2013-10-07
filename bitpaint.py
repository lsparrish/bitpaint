#!/usr/bin/env python2

"""
bitpaint.py
~~~~~~~~~~~
Analyze the Bitcoin blockchain to track and manage "colored coins" which
are distinguished based on their origin.

Caution:
 - Private keys are stored in plaintext in your configuration file.
 - The ordering-based approach hasn't been tested much yet and might
   be incompatible with other kinds of colored coins.
 - Small coin amounts may be seen as dust by the blockchain, and
   may not confirm without a transaction fee.

License: Please be cautious when using it, but feel free to criticise,
modify and contribute to the code.

If you like it, support it:
    1GsnaaAWYMb7yPwBQ19bSLLMTtsfSyjqg3 (bitfair)
    1D5o3Gwm8hbMzgiWi89JWxpnPKhpjx6DiE (lsparrish)

Changes:
 - Config file now distinguishes lists based on newlines rather than
   plus signs. This adds readability, but breaks compatiblity with the
   old style of config file. Make sure to regenerate or edit the 
   config file for compatibility.
 - Address generation is now handled by bitcoind via the jsonrpc
   interface rather than by python code. This reduces the number of
   libraries we need, since jsonrpc was already a requirement.
"""

# Import libraries
import jsonrpc
from optparse import OptionParser
import urllib2, ConfigParser, simplejson as json, os, binascii
jsonrpc.dumps = json.dumps

### Start: Generic helpers
def JSONtoAmount(value):
    return long(round(value * 1e8))
def AmountToJSON(amount):
    return float(amount / 1e8)
### End: Generic helpers


### Start: Create/Read Config
# Here we create a configuration file if one does not exist already.
# User is asked for details about his bitcoind so the script can connect.
config_file = "bitpaint.conf"
basic_bitpaint_conf = """[bitcoind]
rpchost = %s
rpcport = %s
rpcuser = %s
rpcpwd = %s

[HoldingAddresses]
addresses =
private_keys =
"""
# If the config file does not exists, ask user for details and write one
if not os.path.exists(config_file):
    print "Configuration file bitpaint.conf not found. Creating one..."
    host = raw_input("bitcoind rpc host (default: 127.0.0.1): ")
    if len(host) == 0: host = "127.0.0.1"
    port = raw_input("bitcoind rpc port (default: 8332): ")
    if len(port) == 0: port = "8332"
    user = raw_input("bitcoind rpc username (default: <blank>): ")
    pwd = raw_input("bitcoind rpc password (default: <blank>): ")
    f = open(config_file, 'w')
    f.write(basic_bitpaint_conf % (host,port,user,pwd))
    f.close()

# Parse the config file
reserved_sections = ['bitcoind', 'HoldingAddresses']
config = ConfigParser.ConfigParser()
config.read(config_file)
rpchost = config.get('bitcoind', 'rpchost')
rpcport = config.get('bitcoind', 'rpcport')
rpcuser = config.get('bitcoind', 'rpcuser')
rpcpwd  = config.get('bitcoind', 'rpcpwd')

# Connect to bitcoind
if len(rpcuser) == 0 and len(rpcpwd) == 0:
    bitcoind_connection_string = "http://%s:%s" % (rpchost,rpcport)
else:
    bitcoind_connection_string = "http://%s:%s@%s:%s" % (rpcuser,rpcpwd,rpchost,rpcport)
sp = jsonrpc.ServiceProxy(bitcoind_connection_string)

### End: Create/Read Config

### Start: Config list helper functions
# Get a newline-delimited list from the config file

def configListGet(section, item):
    l=[]
    for s in config.get(section, item).split('\n'):
        s.lstrip()
        if l != '':
            l.append(s)
    if l != []: l.remove('')
    return l

def configListSet(section, item, data):
    datastring='\n'+'\n'.join(data)
    config.set(section, item, datastring)

def configListAppendValue(section, item, value):
    data=configListGet(section, item)
    data.append(value)
    configListSet(section, item, data)

def configListRemoveValue(section, item, value):
    data=configListGet(section, item).remove(value)
    configListSet(section, item, data)

### End: Config list helper functions

### Start: Transaction code
def bc_address_to_hash_160(addr):
    bytes = b58decode(addr, 25)
    return bytes[1:21]

__b58chars = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
__b58base = len(__b58chars)

def b58decode(v, length):
    """ decode v into a string of len bytes
    """
    long_value = 0L
    for (i, c) in enumerate(v[::-1]):
        long_value += __b58chars.find(c) * (__b58base**i)
    result = ''
    while long_value >= 256:
        div, mod = divmod(long_value, 256)
        result = chr(mod) + result
        long_value = div
    result = chr(long_value) + result
    nPad = 0
    for c in v:
        if c == __b58chars[0]: nPad += 1
        else: break
    result = chr(0)*nPad + result
    if length is not None and len(result) != length:
        return None
    return result

def makek():
    # Create a dictionary with address as key and private-key
    # as value
    a = configListGet('HoldingAddress','addresses')
    p = configListGet('HoldingAddress','private_keys')
    k = {}
    for a in zip(a,p):
        k[a[0]] = a[1]
    return k

def maketx(inputs, outputs, send=False):
    # Create a transaction, sign it - possibly send it - but
    # in either case return the raw hex
    # inputs: [('a7813e20045b2f2caf612c589adc7e985029167106a300b6a7157084c26967f5', 1, '1PPgZP53BrcG7hyXdWT9fugewmxL1H8LS3'),...]
    # outputs: [('1KRavVCsvaLi7ZzktHSCE3hPUvhPDhQKhz', 8000000),...]
    ip = []
    for txid,vout,_ in inputs:
        ip.append({"txid": txid, "vout": vout})
    op = {}
    for addr,amnt in outputs:
        op[addr] = AmountToJSON(amnt)
    tx = sp.createrawtransaction(ip,op)
    k = makek()
    ip = []
    pkeys = []
    for txid,vout,addr in inputs:
        ip.append({"txid": txid, "vout": vout, "scriptPubKey": '76a914'+bc_address_to_hash_160(addr).encode('hex')+'88ac'})
        if addr in k:
            pkeys.append(k[addr])
        else:
            pkeys.append(sp.dumpprivkey(addr))
    final_t = sp.signrawtransaction(tx,ip,pkeys)
    if send:
        sp.sendrawtransaction(tx)
    else:
        print final_t['hex']
    return final_t['hex']

### End: Transaction code


### Start: Blockchain Inspection/Traversion code
def translate_bctx_to_bitcoindtx(tx_bc):
    tx = {}
    tx['locktime'] = 0
    tx['txid'] = tx_bc['hash']
    tx['version'] = tx_bc['ver']
    tx['vin'] = []
    tx['vout'] = []
    for i in tx_bc['inputs']:
        v = {}
        v['scriptSig'] = {'asm': '', 'hex': ''}
        v['sequence'] = 4294967295
        v['txid'] = json.loads(urllib2.urlopen("http://blockchain.info/rawtx/%s" % (i['prev_out']['tx_index'],)).read())['hash']
        v['vout'] = i['prev_out']['n']
        tx['vin'].append(v)
    for i in range(len(tx_bc['out'])):
        o = tx_bc['out'][i]
        v = {}
        v['n'] = i
        v['scriptPubKey'] = {}
        v['scriptPubKey']['addresses'] = [o['addr']]
        v['scriptPubKey']['asm'] = []
        v['scriptPubKey']['hex'] = []
        v['scriptPubKey']['reqSigs'] = 1,
        v['scriptPubKey']['type'] = 'pubkeyhash'
        v['value'] = float(o['value'])/1e8
        tx['vout'].append(v)
    return tx

def gettx(txid):
    # Get the information of a single transaction, using
    # the bitcoind API
    try:
        tx_raw = sp.getrawtransaction(txid)
        tx = sp.decoderawtransaction(tx_raw)
    except:
        print "Error getting transaction "+txid+" details from bitcoind, trying blockchain.info"
        print "http://blockchain.info/rawtx/%s" % (txid,)
        tx_bc = json.loads(urllib2.urlopen("http://blockchain.info/rawtx/%s" % (txid,)).read())
        tx = translate_bctx_to_bitcoindtx(tx_bc)
    return tx

def getaddresstxs(address):
    # Get all transactions associated with an address.
    # Uses blockchain.info to get this, bitcoind API
    # apparently has no equivalent function.
    address_url="http://blockchain.info/address/"+address+"?format=json"
    address_info = json.loads(urllib2.urlopen(address_url).read())
    tx_list = []
    for tx in address_info['txs']:
        tx_list.append(tx['hash'])
    return tx_list

def getholderschange(txid):
    # Get a list of the new holders and old holders represented by a
    # single transaction, given as the txid.
    tid = txid.split(":")
    tx = gettx(tid[0])
    new_holders = []
    old_holders = []
    for i in tx['vin']:
        old_holders.append(i['txid']+":"+str(i['vout']))
    for o in tx['vout']:
        new_holders.append((o['scriptPubKey']['addresses'][0], o['value']))
    return new_holders, old_holders

def spentby(tx_out):
    # Return the id of the transaction which spent the given txid/#
    # if single_input is true, it only returns if the tx_out was used as a single
    # input to the transaction.
    # This is because it is not possible to follow a colored coin across a transaction
    # with multiple inputs
    tid = tx_out.split(":")
    tx = gettx(tid[0])
    address = tx['vout'][int(tid[1])]['scriptPubKey']['addresses'][0]
    tx_list = getaddresstxs(address)
    for t in tx_list:
        outputs,inputs = getholderschange(t)
        for i in inputs:
            if i == tx_out:
                return t
    return None

def match_outputs_to_inputs(input_values, output_values):
    output_belongs_to_input = [-1]*len(output_values)
    current_color_number = -1
    current_color_total = 0.0
    current_color_max = -1
    for i in range(len(output_values)):
        output_value = output_values[i]
        while current_color_total+output_value > current_color_max:
            current_color_number += 1
            current_color_total = 0.0
            if current_color_number >= len(input_values): return output_belongs_to_input
            current_color_max = input_values[current_color_number]
        output_belongs_to_input[i] = current_color_number
        current_color_total += output_value
    return output_belongs_to_input

def get_relevant_outputs(tx_data,prevout_txid):
    global lost_track
    relevant_outputs = []
    input_values = []
    output_values = []
    input_colors = [-1]*len(tx_data['vin'])
    for pon in range(len(tx_data['vin'])):
        po = tx_data['vin'][pon]
        p_tid = po['txid']+":"+str(po['vout'])
        if p_tid == prevout_txid:
            input_colors[pon] = 0
        po_data = gettx(po['txid'])
        input_values.append(po_data['vout'][po['vout']]['value'])
    for pon in range(len(tx_data['vin'])):
        p_tid = po['txid']+":"+str(po['vout'])
        if p_tid in lost_track:
            po_data = gettx(po['txid'])
            input_values[input_colors.index(0)] += po_data['vout'][po['vout']]['value']
            input_values[pon] = 0
            lost_track.remove(p_tid)
    for o in tx_data['vout']:
        output_values.append(o['value'])
    output_colors = match_outputs_to_inputs(input_values, output_values)
    for o in range(len(output_colors)):
        if output_colors[o] == 0:
            relevant_outputs.append(tx_data['txid']+":"+str(o))
    return relevant_outputs

def rec(prevout_txid, root_tx):
    holder_list = []
    spent_by = spentby(prevout_txid)
    txid,n = prevout_txid.split(":")
    if spent_by is None:
        tx_data = gettx(txid)
        o = tx_data['vout'][int(n)]
        holder_list.append((o['scriptPubKey']['addresses'][0],o['value'],prevout_txid))
        return holder_list
    tx_data = gettx(spent_by)
    relevant_outputs = get_relevant_outputs(tx_data,prevout_txid)
    if len(relevant_outputs) == 0:
        lost_track.append(spent_by)
    for ro in relevant_outputs:
        hl = rec(ro,root_tx)
        for h in hl:
            holder_list.append(h)
    return holder_list

lost_track = []
def get_current_holders(root_tx_out):
    # Get the current holders of the "colored coin" with
    # the given root (a string with txid+":"+n_output)
    global lost_track
    lost_track = []
    return rec(root_tx_out,root_tx_out)

def get_unspent(addr):
    # Get the unspent transactions for an address
    # * Following section is disabled because blockchain.info has a bug that
    #   returns the wrong transaction IDs.
    #d = json.loads(urllib2.urlopen('http://blockchain.info/unspent?address=%s' % addr).read())
    #return d
    # * Start of blockchain.info bug workaround:
    txs = getaddresstxs(addr)
    received = []
    sent = []
    for txid in txs:
        tx = gettx(txid)
        for i in tx['vin']:
            prev_out = gettx(i['txid'])
            for po in prev_out['vout']:
                n = po['n']
                po = po['scriptPubKey']
                if po['type'] == 'pubkeyhash':
                    if po['addresses'][0] == addr:
                        sent.append(i['txid']+":"+str(n))
        for o in tx['vout']:
            n = o['n']
            o = o['scriptPubKey']
            if o['type'] == 'pubkeyhash':
                if o['addresses'][0] == addr:
                    received.append(txid+":"+str(n))
    unspent = []
    for r in received:
        if r not in sent:
            d = {}
            txid,n = r.split(":")
            d['tx_hash'] = txid
            d['tx_output_n'] = int(n)
            d['value'] = int(1e8*gettx(txid)['vout'][int(n)]['value'])
            unspent.append(d)
    return unspent
    # * End of blockchain.info bug workaround


def get_non_asset_funds(addr):
    unspent = get_unspent(addr)
    asset_txids = []
    for s in config.sections():
        if s in reserved_sections: continue
        for txid in configListGet(s,'txid'):
            asset_txids.append(txid)
    naf = []
    for u in unspent:
        txid = u['tx_hash']+":"+str(u['tx_output_n'])
        if not txid in asset_txids:
            naf.append(u)
    return naf

### End: Blockchain Inspection/Traversion code


### Start: "User-facing" methods
def generate_holding_address():
    # Generate an address, add it to the config file
    addr=sp.getnewaddress()
    pkey=sp.dumpprivkey(addr)
    configListAppendValue("HoldingAddresses", "addresses", addr)
    configListAppendValue("HoldingAddresses", "private_keys", pkey)
    config.write(open(config_file,'w'))
    return "Address added: "+addr

def update_tracked_coins(assetname):
    # Update the list of owners of a tracked coin
    # and write to the config file
    root_tx = configListGet(assetname, "root_tx")[0]
    current_holders = get_current_holders(root_tx)
    holding_addresses = []
    holding_amounts = []
    holding_txids = []
    total = 0.0
    for h in current_holders:
        holding_addresses.append(h[0])
        holding_amounts.append(str(h[1]))
        holding_txids.append(h[2])
    configListSet(assetname, "holders", holding_addresses)
    configListSet(assetname, "amounts", holding_amounts)
    configListSet(assetname, "txid", holding_txids)
    config.write(open(config_file,'w'))

def start_tracking_coins(assetname,txid_n):
    # Give a name of a tracked coin, together with a
    # root output that will be used to track it.
    # Write this to the config file, and update the
    # list of owners.
    if assetname in config.sections():
        return assetname+" already exists."
    config.add_section(assetname)
    configListSet(assetname, "root_tx", [txid_n])
    configListSet(assetname, "holders", [])
    configListSet(assetname, "amounts", [])
    configListSet(assetname, "txid", [])
    config.write(open(config_file,'w'))
    update_tracked_coins(assetname)

def show_holders(assetname):
    holders = configListGet(assetname, "holders")
    amounts = configListGet(assetname, "amounts")
    txids = configListGet(assetname,"txid")
    total = 0.0
    print "*** %s ***" % (assetname,)
    for h in zip(holders,amounts,txids):
        print h[0],h[1],h[2]
        total += float(h[1])
    print "** Total %s: %f **" % (assetname,total)

def show_my_holdings():
    sections = config.sections()
    my_holding_addresses = configListGet('HoldingAddresses', 'addresses')
    for s in sections:
        if s in reserved_sections: continue
        holders = configListGet(s, "holders")
        amounts = configListGet(s, "amounts")
        txids = configListGet(s, "txid")
        for h in holders:
            if h in my_holding_addresses:
                total_dividends = 0.0
                for naf in get_non_asset_funds(h):
                    total_dividends += float(naf['value'])/1e8
                print s,amounts[holders.index(h)],"( div:",total_dividends,")",h,txids[holders.index(h)]

def show_my_holding_addresses():
    my_holding_addresses = configListGet('HoldingAddresses', 'addresses')
    for a in my_holding_addresses:
        print a

def show_colors():
    sections = config.sections()
    for s in sections:
        if s in reserved_sections: continue
        print s,config.get(s, 'root_tx')[0]

def transfer_asset(sender, receivers,fee_size=None):
    address,txid,n = sender.split(":")
    tx_input = [(txid, int(n), address)]
    tx_outputs = []
    for l in receivers.split(","):
        address,amount = l.split(":")
        tx_outputs.append((address,int(float(amount)*1e8)))
    if fee_size:
        fee_p_out = sp.listunspent()[0]
        in_addr = base58_check_encode(binascii.unhexlify(fee_p_out['scriptPubKey'][6:-4]))
        change_address = config.get("bitcoind","change_address")
        change_amount = fee_p_out['amount']-fee_size
        tx_input.append((fee_p_out['txid'],fee_p_out['vout'],in_addr))
        tx_outputs.append((change_address, int(1e8*change_amount)))
    raw_transaction = maketx(tx_input, tx_outputs)

def pay_to_shareholders(assetname, wallet_acct, total_payment_amount):
    holders = configListGet(assetname, "holders")
    amounts = configListGet(assetname, "amounts")
    total = 0.0
    for a in amounts:
        total += float(a)
    payouts = {}
    for h,a in zip(holders,amounts):
        d = total_payment_amount*float(a)/total
        payouts[h] = d
    sp.sendmany(wallet_acct,payouts)
    print "Payouts made:"
    for k in payouts.keys():
        print k,":",payouts[k]

def transfer_others(transfer_other_from,transfer_other_to):
    naf = get_non_asset_funds(transfer_other_from)
    fee = int(1e8*0.005)
    total_value = 0
    inputs = []
    for u in naf:
        total_value += u['value']
        i = (u['tx_hash'], u['tx_output_n'], transfer_other_from)
        inputs.append(i)
    outputs = [(transfer_other_to, total_value-fee)]
    maketx(inputs,outputs,send=False)
    print "Paid",float(total_value-fee)/1e8,"to",transfer_other_to


if __name__ == '__main__':
    # Process command-line options
    parser = OptionParser()
    parser.add_option('-p', '--paint', help='Paint coins for tracking. <asset:txid:n>', dest='asset_txid_n', action='store')
    parser.add_option('-n', '--new-address', help='Create new holding address for colored coins', dest='gen_address', default=False, action='store_true')
    parser.add_option('-l', '--list-colors', help='List of names of painted coins being tracked', dest='list_colors', default=False, action='store_true')
    parser.add_option('-u', '--update-ownership', help='Update ownership info for painted coins', dest='update_name', action='store')
    parser.add_option('-o', '--owners', help='Show owners of painted coins', dest="holders_name", action="store")
    parser.add_option('-m', '--my-holdings', help='Show holdings at my addresses', dest="show_holdings", action="store_true")
    parser.add_option('-a', '--holding-addresses', help='Show my holding addresses', dest="show_addresses", action="store_true")
    parser.add_option('-f', '--transfer-from', help='Asset to transfer to another address. address:txid:n', dest='transfer_from', action="store")
    parser.add_option('-t', '--transfer-to', help='Address to transfer asset to. address:amount,...', dest='transfer_to', action="store")
    parser.add_option('-d', '--pay-holders', help="Pay from your bitcoind wallet to asset holders: <asset_name>:<wallet_acctname>:<payout_amount>", dest="pay_to_holders", action="store")
    parser.add_option('-w', '--fee', help="Pay a transaction fee from your wallet when transferring an asset: <amount>", dest="fee", action="store")
    parser.add_option('-x', '--transfer-other-from', help='Transfer bitcoins UNRELATED to the tracked address/coins away from this address', dest="transfer_other_from", action="store")
    parser.add_option('-y', '--transfer-other-to', help='Transfer bitcoins UNRELATED to the tracked address/coins to this address', dest="transfer_other_to", action="store")
    opts, args = parser.parse_args()

    if opts.gen_address:
        print generate_holding_address()
    if opts.asset_txid_n:
        asset,txid,n = opts.asset_txid_n.split(":")
        start_tracking_coins(asset,txid+":"+n)
    if opts.holders_name:
        show_holders(opts.holders_name)
    if opts.update_name:
        update_tracked_coins(opts.update_name)
    if opts.list_colors:
        show_colors()
    if opts.show_holdings:
        show_my_holdings()
    if opts.show_addresses:
        show_my_holding_addresses()
    if opts.pay_to_holders:
        asset_name, wallet_acct_name, amount = opts.pay_to_holders.split(":")
        pay_to_shareholders(asset_name, wallet_acct_name, float(amount))
    if opts.transfer_from or opts.transfer_to:
        if opts.transfer_to and opts.transfer_from:
            if opts.fee:
                transfer_asset(opts.transfer_from, opts.transfer_to,fee_size=float(opts.fee))
            else:
                transfer_asset(opts.transfer_from, opts.transfer_to)
        else:
            print "Make sure you give both a source and destination"
    if opts.transfer_other_from or opts.transfer_other_to:
        if opts.transfer_other_to and opts.transfer_other_from:
            transfer_others(opts.transfer_other_from,opts.transfer_other_to)
        else:
            print "Make sure you give both a source and destination"
