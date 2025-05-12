interface IRouter {
    host: string;
    ip_addresses: string[];
    name: string;
    position: [number, number];
    neightbors: string[];
    prefix: string;
    shortname: string;
    fetching?: boolean;
    error?: boolean;
    status?: IStatus;
}

interface IStatus {
    timestamp: number;
    revision: string;
    revision_commit: string;
    host_info?: {
        kernel: string;
        os: string;
        arch: string;
        docker_version: string;
    },
    tls: {
        expiry: number | null,
        error: string | null,
    },
    'ws-tls': boolean,
    site_cert_expiry: number,
    services: Record<string, {
        image: string;
        status: string;
        running: boolean;
    }>;
    nfd: {
        version: string;
        uptime: string;
    },
    nlsr: {
        version: string;
    },
    ndnping: Record<string, number | null>,
}