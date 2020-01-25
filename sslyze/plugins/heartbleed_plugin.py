import socket
import types
from concurrent.futures._base import Future
from dataclasses import dataclass
from typing import List, Optional

from nassl._nassl import WantReadError
from nassl.ssl_client import OpenSslVersionEnum

from sslyze.plugins.plugin_base import ScanCommandResult, ScanCommandImplementation, ScanJob, ScanCommandExtraArguments
from tls_parser.alert_protocol import TlsAlertRecord
from tls_parser.exceptions import NotEnoughData
from tls_parser.handshake_protocol import TlsHandshakeRecord, TlsHandshakeTypeByte
from tls_parser.heartbeat_protocol import TlsHeartbeatRequestRecord
from tls_parser.parser import TlsRecordParser
from tls_parser.record_protocol import TlsVersionEnum

from sslyze.server_connectivity_tester import ServerConnectivityInfo


@dataclass(frozen=True)
class HeartbleedScanResult(ScanCommandResult):
    """The result of testing a server for the Heartbleed vulnerability.

    Attributes:
        is_vulnerable_to_heartbleed: True if the server is vulnerable to the Heartbleed attack.
    """

    is_vulnerable_to_heartbleed: bool


class HeartbleedImplementation(ScanCommandImplementation):
    @classmethod
    def scan_jobs_for_scan_command(
        cls, server_info: ServerConnectivityInfo, extra_arguments: Optional[ScanCommandExtraArguments] = None
    ) -> List[ScanJob]:
        if extra_arguments:
            raise ValueError("This plugin does not take extra arguments")

        return [ScanJob(function_to_call=_test_heartbleed, function_arguments=[server_info])]

    @classmethod
    def result_for_completed_scan_jobs(
        cls, server_info: ServerConnectivityInfo, completed_scan_jobs: List[Future]
    ) -> ScanCommandResult:
        if len(completed_scan_jobs) != 1:
            raise RuntimeError(f"Unexpected number of scan jobs received: {completed_scan_jobs}")

        return HeartbleedScanResult(is_vulnerable_to_heartbleed=completed_scan_jobs[0].result())


def _test_heartbleed(server_info: ServerConnectivityInfo) -> bool:
    if server_info.tls_probing_result.highest_tls_version_supported >= OpenSslVersionEnum.TLSV1_3:
        # The server uses a recent version of OpenSSL and it cannot be vulnerable to Heartbleed
        return False

    ssl_connection = server_info.get_preconfigured_ssl_connection()
    # Replace nassl.sslClient.do_handshake() with a heartbleed checking SSL handshake so that all the SSLyze options
    # (startTLS, proxy, etc.) still work
    ssl_connection.ssl_client.do_handshake = types.MethodType(_do_handshake_with_heartbleed, ssl_connection.ssl_client)

    is_vulnerable_to_heartbleed = False
    try:
        # Start the SSL handshake
        ssl_connection.connect()
    except _VulnerableToHeartbleed:
        # The test was completed and the server is vulnerable
        is_vulnerable_to_heartbleed = True
    except _NotVulnerableToHeartbleed:
        # The test was completed and the server is NOT vulnerable
        pass
    finally:
        ssl_connection.close()

    return is_vulnerable_to_heartbleed


class _VulnerableToHeartbleed(Exception):
    """Exception to raise during the handshake to hijack the flow and test for Heartbleed.
    """


class _NotVulnerableToHeartbleed(Exception):
    """Exception to raise during the handshake to hijack the flow and test for Heartbleed.
    """


def _do_handshake_with_heartbleed(self):  # type: ignore
    """Modified do_handshake() to send a heartbleed payload and return the result.
    """
    try:
        # Start the handshake using nassl - will throw WantReadError right away
        self._ssl.do_handshake()
    except WantReadError:
        # Send the Client Hello
        len_to_read = self._network_bio.pending()
        while len_to_read:
            # Get the data from the SSL engine
            handshake_data_out = self._network_bio.read(len_to_read)
            # Send it to the peer
            self._sock.send(handshake_data_out)
            len_to_read = self._network_bio.pending()

    # Build the heartbleed payload - based on
    # https://blog.mozilla.org/security/2014/04/12/testing-for-heartbleed-vulnerability-without-exploiting-the-server/
    payload = TlsHeartbeatRequestRecord.from_parameters(
        tls_version=TlsVersionEnum[self._ssl_version.name], heartbeat_data=b"\x01" * 16381
    ).to_bytes()

    payload += TlsHeartbeatRequestRecord.from_parameters(
        TlsVersionEnum[self._ssl_version.name], heartbeat_data=b"\x01\x00\x00"
    ).to_bytes()

    # Send the payload
    self._sock.send(payload)

    # Retrieve the server's response - directly read the underlying network socket
    # Retrieve data until we get to the ServerHelloDone
    # The server may send back a ServerHello, an Alert, a CertificateRequest or may just close the connection
    did_receive_hello_done = False
    remaining_bytes = b""
    while not did_receive_hello_done:
        try:
            tls_record, len_consumed = TlsRecordParser.parse_bytes(remaining_bytes)
            remaining_bytes = remaining_bytes[len_consumed::]
        except NotEnoughData:
            # Try to get more data
            try:
                raw_ssl_bytes = self._sock.recv(16381)
            except socket.error:
                # Server closed the connection as soon as it received the Heartbleed payload
                raise _NotVulnerableToHeartbleed()

            if not raw_ssl_bytes:
                # No data?
                raise _NotVulnerableToHeartbleed()

            remaining_bytes = remaining_bytes + raw_ssl_bytes
            continue

        if isinstance(tls_record, TlsHandshakeRecord):
            # Does the record contain a ServerDone message?
            for handshake_message in tls_record.subprotocol_messages:
                if handshake_message.handshake_type == TlsHandshakeTypeByte.SERVER_DONE:
                    did_receive_hello_done = True
                    break
            # If not, it could be a ServerHello, Certificate or a CertificateRequest if the server requires client auth
        elif isinstance(tls_record, TlsAlertRecord):
            # Server returned a TLS alert
            break
        else:
            raise ValueError("Unknown record? Type {}".format(tls_record.header.type))

    is_vulnerable_to_heartbleed = False
    if did_receive_hello_done:
        expected_heartbleed_payload = b"\x01" * 10
        if expected_heartbleed_payload in remaining_bytes:
            # Server replied with our hearbeat payload
            is_vulnerable_to_heartbleed = True
        else:
            try:
                raw_ssl_bytes = self._sock.recv(16381)
            except socket.error:
                # Server closed the connection after receiving the heartbleed payload
                raise _NotVulnerableToHeartbleed()

            if expected_heartbleed_payload in raw_ssl_bytes:
                # Server replied with our hearbeat payload
                is_vulnerable_to_heartbleed = True

    if is_vulnerable_to_heartbleed:
        raise _VulnerableToHeartbleed()
    else:
        raise _NotVulnerableToHeartbleed()


# TODO
class CliConnector:
    def as_text(self) -> List[str]:
        heartbleed_txt = (
            "VULNERABLE - Server is vulnerable to Heartbleed"
            if self.is_vulnerable_to_heartbleed
            else "OK - Not vulnerable to Heartbleed"
        )

        return [self._format_title(self.scan_command.get_title()), self._format_field("", heartbleed_txt)]
