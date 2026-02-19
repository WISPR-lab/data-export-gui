<template>
  <v-container style="max-width: 1200px;">
    <v-row align="center" style="margin-bottom: 8px;">
      <h2 style="margin: 0;">🛠 Debug</h2>
    </v-row>

    <!-- Nav links -->
    <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 20px;">
      <router-link
        v-for="s in SECTIONS"
        :key="s.path"
        :to="'/debug/' + s.path"
        style="text-decoration: none;"
      >
        <v-btn
          small
          :color="currentSection === s.path ? 'primary' : ''"
          :outlined="currentSection !== s.path"
        >{{ s.label }}</v-btn>
      </router-link>
    </div>

    <!-- ── OPFS section ── -->
    <div v-if="currentSection === 'opfs'">
      <v-row align="center" style="margin-bottom: 12px;">
        <v-btn small @click="refreshOPFS" :loading="opfsLoading" color="primary">Refresh</v-btn>
        <v-btn small @click="nukeAll" color="error" style="margin-left: 8px;">Nuke All</v-btn>
        <v-btn small @click="clearTempOnly" color="warning" style="margin-left: 8px;">Clear tmpstore</v-btn>
        <span style="margin-left: 16px; color: #888; font-size: 12px;">{{ opfsStatus }}</span>
      </v-row>
      <div v-if="opfsLoading" style="color: #888; font-family: monospace;">Loading...</div>
      <div v-else-if="opfsTree.length === 0" style="color: #888; font-family: monospace;">OPFS is empty.</div>
      <div v-else style="font-family: monospace;">
        <div
          v-for="node in opfsTree"
          :key="node.path"
          :style="{ paddingLeft: (node.depth * 20) + 'px', lineHeight: '1.8', cursor: node.kind === 'file' ? 'pointer' : 'default' }"
          @click="node.kind === 'file' && readFile(node)"
        >
          <span v-if="node.kind === 'directory'">📁 {{ node.name }}/</span>
          <span v-else style="color: #1a73e8; text-decoration: underline;">
            📄 {{ node.name }} <span style="color: #888; font-size: 11px;">({{ node.size }})</span>
          </span>
        </div>
      </div>
    </div>

    <!-- ── Table section ── -->
    <div v-else-if="currentTable">
      <v-row align="center" style="margin-bottom: 12px;">
        <v-btn small @click="loadTable" :loading="tableLoading" color="primary">Refresh</v-btn>
        <span style="margin-left: 12px; color: #888; font-size: 12px;">{{ tableStatus }}</span>
      </v-row>
      <div v-if="tableLoading" style="color: #888;">Loading...</div>
      <div v-else style="overflow-x: auto;">
        <table style="border-collapse: collapse; width: 100%; font-size: 12px; font-family: monospace;">
          <thead>
            <tr>
              <th
                v-for="col in tableCols"
                :key="col"
                style="text-align: left; padding: 4px 10px; border-bottom: 2px solid #ccc; white-space: nowrap; background: #f5f5f5;"
              >{{ col }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="tableRows.length === 0">
              <td
                :colspan="tableCols.length || 1"
                style="padding: 10px; color: #888; text-align: center; font-style: italic;"
              >Table is empty.</td>
            </tr>
            <tr
              v-for="(row, i) in tableRows"
              :key="i"
              :style="{ background: i % 2 === 0 ? '#fff' : '#fafafa' }"
            >
              <td
                v-for="col in tableCols"
                :key="col"
                style="padding: 3px 10px; border-bottom: 1px solid #eee; max-width: 280px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; cursor: pointer;"
                :title="String(row[col])"
                @click="showCell(col, row[col])"
              >{{ row[col] }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- File content dialog -->
    <v-dialog v-model="fileDialog" max-width="800">
      <v-card>
        <v-card-title style="word-break: break-all;">{{ selectedFile }}</v-card-title>
        <v-card-text>
          <pre style="max-height: 500px; overflow: auto; font-size: 12px; background: #f5f5f5; padding: 12px; border-radius: 4px;">{{ fileContent }}</pre>
        </v-card-text>
        <v-card-actions><v-btn text @click="fileDialog = false">Close</v-btn></v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Cell expand dialog -->
    <v-dialog v-model="cellDialog" max-width="700">
      <v-card>
        <v-card-title style="font-size: 14px;">{{ cellTitle }}</v-card-title>
        <v-card-text>
          <pre style="max-height: 500px; overflow: auto; font-size: 12px; background: #f5f5f5; padding: 12px; border-radius: 4px; white-space: pre-wrap;">{{ cellContent }}</pre>
        </v-card-text>
        <v-card-actions><v-btn text @click="cellDialog = false">Close</v-btn></v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script>
import { getDB } from '@/database/index.js';

var DB_TABLES = ['uploads', 'uploaded_files', 'raw_data', 'events', 'auth_devices_initial', 'event_comments'];

var SECTIONS = [
  { path: 'opfs', label: '📁 OPFS' }
].concat(DB_TABLES.map(function(t) { return { path: t, label: t }; }));

export default {
  name: 'DebugView',
  data: function() {
    return {
      SECTIONS: SECTIONS,
      DB_TABLES: DB_TABLES,
      // OPFS
      opfsTree: [],
      opfsLoading: false,
      opfsStatus: '',
      fileDialog: false,
      selectedFile: '',
      fileContent: '',
      // Table
      tableRows: [],
      tableCols: [],
      tableLoading: false,
      tableStatus: '',
      // Cell expand
      cellDialog: false,
      cellTitle: '',
      cellContent: '',
    };
  },
  computed: {
    currentSection: function() {
      return this.$route.params.section || 'opfs';
    },
    currentTable: function() {
      return DB_TABLES.indexOf(this.currentSection) !== -1 ? this.currentSection : null;
    },
  },
  watch: {
    currentSection: function(val) {
      if (val === 'opfs') {
        this.refreshOPFS();
      } else if (DB_TABLES.indexOf(val) !== -1) {
        this.loadTable();
      }
    },
  },
  mounted: function() {
    if (this.currentSection === 'opfs') {
      this.refreshOPFS();
    } else if (this.currentTable) {
      this.loadTable();
    }
  },
  methods: {
    // ── OPFS ──────────────────────────────────────────────────────────
    refreshOPFS: async function() {
      this.opfsLoading = true;
      this.opfsStatus = '';
      this.opfsTree = [];
      try {
        var root = await navigator.storage.getDirectory();
        await this._walk(root, '', 0);
        var fileCount = this.opfsTree.filter(function(n) { return n.kind === 'file'; }).length;
        this.opfsStatus = fileCount + ' file(s)';
      } catch (e) {
        this.opfsStatus = 'Error: ' + e.message;
      } finally {
        this.opfsLoading = false;
      }
    },
    _walk: async function(dirHandle, pathPrefix, depth) {
      this.opfsTree.push({ kind: 'directory', name: dirHandle.name || '(root)', path: pathPrefix || '/', depth: depth, size: '' });
      for await (var entry of dirHandle.entries()) {
        var name = entry[0];
        var handle = entry[1];
        if (handle.kind === 'directory') {
          await this._walk(handle, pathPrefix + name + '/', depth + 1);
        } else {
          var file = await handle.getFile();
          var size = file.size > 1024 ? (file.size / 1024).toFixed(1) + ' KB' : file.size + ' B';
          this.opfsTree.push({ kind: 'file', name: name, path: pathPrefix + name, depth: depth + 1, size: size, handle: handle });
        }
      }
    },
    readFile: async function(node) {
      try {
        var file = await node.handle.getFile();
        var text = await file.text();
        this.selectedFile = node.path;
        try { this.fileContent = JSON.stringify(JSON.parse(text), null, 2); }
        catch (e) { this.fileContent = text; }
        this.fileDialog = true;
      } catch (e) {
        this.opfsStatus = 'Could not read file: ' + e.message;
      }
    },
    nukeAll: async function() {
      if (!confirm('Delete everything in OPFS (including database)?')) return;

      this.opfsStatus = 'closing db'
      await closeDB();
      
      var root = await navigator.storage.getDirectory();
      for await (var entry of root.entries()) {
        await root.removeEntry(entry[0], { recursive: true });
      }
      this.opfsStatus = 'Nuked.';
      await this.refreshOPFS();
    },
    clearTempOnly: async function() {
      var root = await navigator.storage.getDirectory();
      try {
        var tmpDir = await root.getDirectoryHandle('tmpstore');
        for await (var entry of tmpDir.entries()) {
          await tmpDir.removeEntry(entry[0], { recursive: true });
        }
        this.opfsStatus = 'tmpstore cleared.';
      } catch (e) {
        this.opfsStatus = 'tmpstore not found or already empty.';
      }
      await this.refreshOPFS();
    },
    // ── DB table ──────────────────────────────────────────────────────
    loadTable: async function() {
      var table = this.currentTable;
      if (!table) return;
      this.tableLoading = true;
      this.tableStatus = '';
      this.tableRows = [];
      this.tableCols = [];
      try {
        var db = await getDB();
        var rows = await db.exec(
          'SELECT * FROM ' + table + ' LIMIT 500',
          { returnValue: 'resultRows', rowMode: 'object' }
        );
        this.tableRows = rows || [];
        if (rows && rows.length > 0) {
          this.tableCols = Object.keys(rows[0]);
          this.tableStatus = rows.length + ' row(s)' + (rows.length === 500 ? ' (limit 500)' : '');
        } else {
          // Fetch column names via PRAGMA even when table is empty
          var pragmaRows = await db.exec(
            'PRAGMA table_info(' + table + ')',
            { returnValue: 'resultRows', rowMode: 'object' }
          );
          this.tableCols = (pragmaRows || []).map(function(r) { return r.name; });
          this.tableStatus = '0 rows';
        }
      } catch (e) {
        this.tableStatus = '\u274c ' + e.message;
      } finally {
        this.tableLoading = false;
      }
    },
    showCell: function(col, val) {
      this.cellTitle = col;
      try { this.cellContent = JSON.stringify(JSON.parse(val), null, 2); }
      catch (e) { this.cellContent = String(val !== null && val !== undefined ? val : '(null)'); }
      this.cellDialog = true;
    },
  },
};
</script>
