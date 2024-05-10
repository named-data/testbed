<template>
  <div class="outer">
    <table class="styled-table">
      <thead>
        <tr>
          <th></th>
          <th>Prefix</th>
          <th>HTTPS</th>

          <th>Revision</th>
          <th>NFD Version</th>
          <th>NLSR Version</th>

          <th v-for="service in services">{{ service }}</th>

          <th v-for="node in routers"> {{ node.shortname }} </th>
        </tr>
      </thead>

      <tbody>
        <tr v-for="(router, name) in routers" :key="name">
          <td :class="{
            okay: !!router.status,
            error: router.error,
            warning: router.fetching,
          }">
            {{ router.shortname }}
          </td>

          <td>{{ router.prefix }}</td>
          <td><a :href="`https://${router.host}`" target="_blank">{{ router.host }}</a></td>

          <td>
            <a v-if="router.status?.revision"
                :href="getRevUrl(router)"
                target="_blank">
                {{ router.status?.revision }}
            </a>
          </td>
          <td>{{ router.status?.nfd?.version }}</td>
          <td>{{ router.status?.nlsr?.version }}</td>

          <td v-for="service in services">
            <span v-if="router.status?.services[service]" :class="{
              error: !router.status.services[service].running,
            }">
              {{ router.status.services[service].status }}
            </span>
          </td>

          <td v-for="node in routers" :class="{
              error: !router.status?.ndnping[node.shortname],
              okay: router.status?.ndnping[node.shortname] ?? 0 > 0,
            }">
              {{ router.status?.ndnping[node.shortname] || '' }}
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';

import { connectToNetwork } from "@ndn/autoconfig";
import { fetch } from "@ndn/segmented-object";
import { retrieveMetadata } from "@ndn/rdr";

const ROUTERS_JSON = '/ndn/edu/ucla/file-server/routers.json';
const STATUS_SFX = '/file-server/status.json';
const TESTBED_REPO = 'https://github.com/UCLA-IRL/testbed';

interface IRouter {
  host: string;
  ip_addresses: string[];
  name: string;
  position: [number, number];
  prefix: string;
  shortname: string;
  fetching?: boolean;
  error?: boolean;
  status?: IStatus;
};

interface IStatus {
  timestamp: number;
  revision: string;
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
};

export default defineComponent({
  name: 'App',

  data: () => ({
    connectedFace: String(),
    routers: {} as Record<string, IRouter>,
    services: [] as string[],
  }),

  async mounted() {
    // Connect to testbed
    const faces = await connectToNetwork();
    if (!faces.length) {
      alert('Failed to connect to testbed');
      return;
    }

    // Connection successful
    this.connectedFace = `${faces[0]}`;
    this.start();
  },

  methods: {
    async start() {
      // Get router list
      this.routers = JSON.parse(await this.cat(ROUTERS_JSON));

      // Get each router's status
      for (const [name, router] of Object.entries(this.routers)) {
        this.refreshRouter(router);
      }
    },

    async refreshRouter(router: IRouter) {
      try {
          router.fetching = true;
          router.status = JSON.parse(await this.cat(router.prefix + STATUS_SFX));
          router.error = false;

          // Get services
          for (const name of Object.keys(router.status?.services ?? {})) {
            if (!this.services.includes(name)) {
              this.services.push(name);
            }
          }
        } catch (err) {
          console.warn(err);
          router.error = true;
          router.status = undefined;
        } finally {
          router.fetching = false;
        }
    },

    async cat(name: string) {
      const metadata = await retrieveMetadata(name, { retx: 3 });
      const bytes = await fetch(metadata.name, {
        cOpts: { retx: 3 }
      });
      return new TextDecoder().decode(bytes);
    },

    getRevUrl(router: IRouter) {
      return `${TESTBED_REPO}/commit/${router.status!.revision}`;
    },
  },
});
</script>

<style scoped>
div.outer {
  width: 100%;
  height: 100vh;
  overflow: auto;
}

table {
  border-collapse: collapse;
  font-family: monospace;
  white-space: nowrap;
  margin: 0;
  border-collapse: separate;
  border-spacing: 0;
  table-layout: fixed;
}

th, td {
  border: 1px solid #888;
  padding: 6px 10px;
}

table thead th:first-child, table tbody td:first-child {
  position: sticky;
  left: 0;
  z-index: 2;
}

table thead th {
  position: sticky;
  top: 0;
  background-color: white;
  z-index: 1;
}

td {
  background-color: white;
}
td.error, td:has(.error) {
  background-color: #ffaaaa !important;
}
td.okay {
  background-color: #aaffaa;
}
td.warning {
  background-color: #ffffaa;
}

a {
  color: blue;
  text-decoration: none;
}
</style>
