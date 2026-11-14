"""software_pegasus: Pegasus WMS workflows (e.g. montage-workflow-v3) on HPC without an HTCondor pool: planning-only userspace Condor (never started), Pegasus 5.0.7 binary, pegasus-mpi-cluster (PMC) rebuilt against the system MPI, sites.yml + pegasus.properties for PMC-only code generation, pegasus-plan --conf, PMC launched under flux run with a wrapper exporting LD_LIBRARY_PATH and dftracer env, rank sizing, dftracer trace verification. Load for any Pegasus workflow work, or on: 'libmpichcxx.so.10 => not found'; successive 'cannot open shared object file' (libmpi_cray.so.12, libpmi.so.0, libpals.so.0); 'File Server not specified for shared-scratch filesystem'; 'FileNotFoundException: .../run0001 (Is a directory)' at MPIExec.generatePMCInputFile; "ModuleNotFoundError: No module named 'six.moves'"; 'ABORT: failure.cpp(22): Invalid DAG record: MAXJOBS'; stage_in tasks hang then exit 256; PMC silent after 'Running PMC cluster with DAG'."""
import json
import re


def _flatten(v):
    if isinstance(v, str):
        return v.splitlines()
    if isinstance(v, dict):
        return [x for i in v.values() for x in _flatten(i)]
    if isinstance(v, list):
        return [x for i in v for x in _flatten(i)]
    return []


def _SOFTWARE_PEGASUS_judge(commands, rules):
    """Apply the rules (forbid / require / require_if / forbid_if regexes) to the proposed commands."""
    items = commands
    if isinstance(commands, str):
        s = commands.strip()
        if s[:1] in "[{":
            try:
                items = json.loads(s)
            except ValueError:
                items = s
    lines = [ln for ln in _flatten(items) if ln.strip()]
    if not lines:
        return {"status": "inconclusive", "checks": [], "verdicts": {},
                "detail": "no commands given: pass the proposed command lines or recipe"}
    text = "\n".join(lines)
    out, verdicts = [], {}
    for r in rules:
        fl = re.I if "i" in r.get("flags", "") else 0
        pat = re.compile(r["pattern"], fl)
        when = re.compile(r["when"], fl) if r.get("when") else None
        kind = r["kind"]
        applies = when is None or bool(when.search(text))
        ok, detail = True, "not applicable"
        if applies and kind in ("forbid", "forbid_if"):
            bad = [ln for ln in lines if pat.search(ln)]
            ok = not bad
            detail = ("found: " + bad[0][:160]) if bad else "absent, as required"
        elif applies and kind in ("require", "require_if"):
            ok = bool(pat.search(text))
            detail = "present" if ok else "missing: " + r["pattern"]
        verdicts[r["id"]] = "n/a" if not applies else ("pass" if ok else "fail")
        out.append({"check": r["id"], "ok": ok, "detail": detail if ok else detail + " -- " + r["why"],
                    "fix": "" if ok else r["fix"]})
    return {"status": "fail" if any(not c["ok"] for c in out) else "pass", "checks": out, "verdicts": verdicts}


def register(mcp):

    @mcp.tool()
    def software_pegasus_recipe(section: str = "") -> str:
        """The build/run/env recipe software_pegasus knows, as structured JSON: architecture, condor_env, env_for_planning, expected_profile, install_condor, install_pegasus, montage, plan, pmc_rebuild, properties, python, run_pmc, runtime_ld_library_path, sites_yml, verify_plan, verify_traces, versions.

        Use before building, configuring or running anything this capability covers, to get its facts as data instead
        of re-reading prose. section: one top-level key of the recipe (architecture, condor_env, env_for_planning, expected_profile, install_condor, install_pegasus, montage, plan, pmc_rebuild, properties, python, run_pmc, runtime_ld_library_path, sites_yml, verify_plan, verify_traces, versions); blank = all of it. Returns JSON
        {status, capability, sections, recipe, checks: [{id, why}] (what software_pegasus_check enforces)} or
        {status: "error", error} for an unknown section.
        """
        recipe = _SOFTWARE_PEGASUS_RECIPE
        if section:
            if section not in recipe:
                return json.dumps({"status": "error", "error": "unknown section %r; one of %s" % (section, sorted(recipe))})
            recipe = {section: recipe[section]}
        return json.dumps({"status": "ok", "capability": "software_pegasus", "sections": sorted(_SOFTWARE_PEGASUS_RECIPE), "recipe": recipe,
                           "checks": [{"id": r["id"], "why": r["why"]} for r in _SOFTWARE_PEGASUS_RULES]})

    @mcp.tool()
    def software_pegasus_check(commands: str = "") -> str:
        """Check a proposed recipe or command list against software_pegasus's rules: no_condor_daemons; no_dagman_submit; plan_requires_conf; no_cluster_horizontal; properties_pmc_generator; pmc_rebuilt_with_mpicxx; pmc_rank_count; no_dag_maxjobs_strip; no_sudo.

        Use on a proposed recipe or command list before running it, and after software_pegasus_recipe to rule on what was
        planned. commands: newline-separated command lines / script text, a JSON list of them, or a JSON object (its
        string values are checked). Deterministic regex rules; nothing runs. Returns JSON {status: pass|fail|inconclusive,
        checks: [{check, ok, detail, fix}], verdicts: {rule id: pass|fail|n/a}}; inconclusive when nothing was given.
        """
        return json.dumps(_SOFTWARE_PEGASUS_judge(commands, _SOFTWARE_PEGASUS_RULES))


_SOFTWARE_PEGASUS_RECIPE = {'architecture': {'executor': 'pegasus-mpi-cluster (PMC): 1 master rank + N worker ranks, one task per worker at a '
                              'time',
                  'planner': 'pegasus-plan with pegasus.code.generator=PMC -> flat TASK/EDGE .dag',
                  'condor': 'planning-time dependency only; never start daemons',
                  'reference': 'https://dftracer.readthedocs.io/en/latest/pegasus_montage.html (LC Corona, '
                               'generalized)'},
 'versions': {'pegasus': '5.0.7 (pegasus-binary-5.0.7-x86_64_rhel_7.tar.gz)',
              'condor': '10.x stripped tarball (CentOS8/RHEL8/AlmaLinux8 all fine on RHEL 8.10)',
              'pmc_mpi_known_good': 'Cray MPICH 9.0.1 + crayclang',
              'pmc_cluster_bug': '--cluster horizontal broken with PMC on 5.0.7',
              'python': '3.9-3.13 for Pegasus API'},
 'install_condor': ['wget '
                    'https://research.cs.wisc.edu/htcondor/tarball/10.x/current/condor-x86_64_CentOS8-stripped.tar.gz '
                    '-O condor.tar.gz',
                    'tar -x -f condor.tar.gz',
                    'mkdir condor && mv condor-*-stripped/* condor/ && rmdir condor-*-stripped',
                    'cd condor && ./bin/make-personal-from-tarball'],
 'condor_env': {'CONDOR_CONFIG': '<condor>/etc/condor_config',
                'PATH_prepend': ['<condor>/bin', '<condor>/sbin'],
                'never': ['condor_master', 'condor_schedd']},
 'install_pegasus': ['wget https://download.pegasus.isi.edu/pegasus/5.0.7/pegasus-binary-5.0.7-x86_64_rhel_7.tar.gz',
                     'tar zxf pegasus-binary-5.0.7-x86_64_rhel_7.tar.gz',
                     'mv pegasus-5.0.7/* pegasus/'],
 'pmc_rebuild': {'commands': ['curl -sL https://github.com/pegasus-isi/pegasus/archive/refs/tags/5.0.7.tar.gz -o '
                              'pegasus-src.tar.gz',
                              'tar xzf pegasus-src.tar.gz pegasus-5.0.7/packages/pegasus-mpi-cluster',
                              'cd pegasus-5.0.7/packages/pegasus-mpi-cluster',
                              'make CXX=$(which mpicxx) prefix=<pegasus>',
                              'cp pegasus-mpi-cluster <pegasus>/bin/pegasus-mpi-cluster'],
                 'why': 'prebuilt links libmpich.so.10 / libmpichcxx.so.10 (ABI v10); Cray ships libmpi_cray.so.12',
                 'build_system': 'plain Makefile using mpicxx',
                 'harmless_warning': 'release-tools/getversion: No such file or directory'},
 'runtime_ld_library_path': {'template': ['/opt/cray/pe/lib64',
                                          '/opt/cray/lib64',
                                          '/opt/cray/pe/papi/<ver>/lib64',
                                          '/opt/cray/pe/pmi/<ver>/lib',
                                          '/opt/cray/pe/mpich/<ver>/ofi/crayclang/<ver>/lib',
                                          '/opt/cray/pe/cce/<ver>/cce/x86_64/lib',
                                          '/opt/cray/pe/cce/<ver>/cce-clang/x86_64/lib',
                                          '/usr/lib64',
                                          '<dftracer-venv>/lib/python3.*/site-packages/dftracer/lib64'],
                             'find_pmi': 'find /opt/cray/pe/pmi -iname libpmi.so.0',
                             'tuolumne': 'libpmi.so.0 / libpmi2.so.0 resolve from /opt/cray/pe/lib64',
                             'annotated_binaries': 'RPATH to libdftracer_core.so but still need Cray PE libs '
                                                   '(libmpi_cray.so.12, libmodules.so.1)'},
 'python': {'PYTHONPATH': '<pegasus>/lib64/python3.6/site-packages',
            'check': 'python3 -c "from Pegasus.api import *"',
            'pip': ['astropy', 'gitpython', 'six'],
            'interpreter': 'pegasus-plan / pegasus-transfer are #!/usr/bin/env python3 scripts: install into the '
                           'first python3 on PATH',
            'six_fix': 'mv <pegasus>/lib64/pegasus/externals/python/six.py{,.bak}'},
 'montage': {'build': ['git clone https://github.com/Caltech-IPAC/Montage.git', 'cd Montage && make'],
             'annotated': 'put dftracer-annotated install_ann/bin FIRST on PATH before montage-workflow.py',
             'dax': 'python3 ./montage-workflow.py --center "<ra dec>" --degrees 1.0 --band dss:DSS2B:blue',
             'degrees': {'1.0': '~4 images / 6 overlaps (good)', '0.3': 'may give 1 image, no overlaps (too small)'}},
 'env_for_planning': {'PATH': '<montage-bin>:<pegasus>/bin:<condor>/bin:<condor>/sbin:$PATH',
                      'PYTHONPATH': '<pegasus>/lib64/python3.6/site-packages',
                      'CONDOR_CONFIG': '<condor>/etc/condor_config'},
 'sites_yml': 'pegasus: "5.0"\n'
              'sites:\n'
              ' - name: local\n'
              '   arch: x86_64\n'
              '   os.type: linux\n'
              '   directories:\n'
              '    - type: sharedScratch\n'
              '      path: <workspace>/scratch\n'
              '      fileServers:\n'
              '       - operation: all\n'
              '         url: file://<workspace>/scratch\n'
              '    - type: localStorage\n'
              '      path: <workspace>/storage\n'
              '      fileServers:\n'
              '       - operation: all\n'
              '         url: file://<workspace>/storage',
 'properties': {'pegasus.code.generator': 'PMC',
                'pegasus.data.configuration': 'sharedfs',
                'pegasus.transfer.links': 'true',
                'note': 'transfer.links / bypass.input.staging do not remove stage_in jobs for remote replicas'},
 'plan': {'command': 'pegasus-plan --conf pegasus.properties --sites local --dir work --output-site local '
                     'data/montage-workflow.yml',
          'never': ['--submit', '--cluster horizontal', 'omitting --conf', 'pegasus-run'],
          'dag': 'work/<user>/pegasus/<name>/run0001/<name>-0.dag'},
 'verify_plan': ["grep -c '^TASK\\|^EDGE' <name>-0.dag   # large",
                 "grep -c '^JOB\\|^MAXJOBS' <name>-0.dag  # must be 0",
                 'ls -la <each file:// path in catalogs/replicas.yml>'],
 'run_pmc': {'command': 'flux proxy <ALLOC_JOBID> flux run -N1 -n<workers+1> bash pmc_wrapper.sh '
                        '<pegasus>/bin/pegasus-mpi-cluster -v $RUN/<name>-0.dag',
             'wrapper': ['#!/bin/bash',
                         'export LD_LIBRARY_PATH="<LD block>"',
                         'export DFTRACER_ENABLE=1',
                         'export DFTRACER_INIT=FUNCTION',
                         'export DFTRACER_INC_METADATA=1',
                         'export DFTRACER_DATA_DIR=all',
                         'export DFTRACER_LOG_FILE=<traces-dir>/<name>',
                         'cd <RUN-dir>',
                         'exec "$@"'],
             'ranks': '-n ~2-4x widest concurrent stage + 1 master (e.g. -n8 = 7 slots on 1 node; -N4 -n32, not '
                      '-n380)',
             'hang_timeout': 'cancel after 2-3 min of only startup output',
             'verbose': '-v on first run',
             'env_inheritance': 'PMC worker-forked tasks inherit the wrapper env -> dftracer on every job'},
 'expected_profile': {'workload': '~1 degree, 4 images, single band, 57 jobs',
                      'runtime': '< 15 min on 1 node with 7-8 workers; ~5 min of it remote stage-in',
                      'success': '[cluster-summary stat="ok", tasks=57, submitted=57, succeeded=57, failed=0, ...] / '
                                 '[info] Workflow suceeded'},
 'verify_traces': {'command': 'ls -la <traces-dir>/*.pfw.gz',
                   'expect': 'one non-empty trace per annotated-binary invocation; 0-byte traces from '
                             'chmod/register/cleanup bookkeeping are fine; mProject/mProjExec largest'}}

_SOFTWARE_PEGASUS_RULES = [{'id': 'no_condor_daemons',
  'kind': 'forbid',
  'pattern': '\\bcondor_(master|schedd)\\b',
  'why': 'Condor is planning-time tooling only; PMC executes the workflow.',
  'fix': 'Do not start Condor daemons; run the DAG with pegasus-mpi-cluster.'},
 {'id': 'no_dagman_submit',
  'kind': 'forbid',
  'pattern': '\\bpegasus-run\\b|pegasus-plan\\b[^\\n]*--submit',
  'why': 'pegasus-run / --submit go through Condor DAGMan, which has no daemons in this architecture.',
  'fix': 'Plan without --submit, then run pegasus-mpi-cluster on the generated .dag.'},
 {'id': 'plan_requires_conf',
  'kind': 'forbid',
  'pattern': '^(?!.*--conf\\b).*\\bpegasus-plan\\b',
  'why': "Without --conf, pegasus.code.generator=PMC is ignored and a DAGMan DAG is emitted ('Invalid DAG record: "
         "MAXJOBS').",
  'fix': 'Pass --conf <pegasus.properties> to every pegasus-plan.'},
 {'id': 'no_cluster_horizontal',
  'kind': 'forbid',
  'pattern': 'pegasus-plan\\b[^\\n]*--cluster\\s+horizontal',
  'why': 'Pegasus 5.0.7 PMC code generator bug: FileNotFoundException run0001 (Is a directory).',
  'fix': 'Drop --cluster horizontal.'},
 {'id': 'properties_pmc_generator',
  'kind': 'require_if',
  'pattern': 'pegasus\\.code\\.generator\\s*=\\s*PMC',
  'when': 'pegasus-plan\\b',
  'why': 'Only pegasus.code.generator=PMC makes the planner emit a TASK/EDGE DAG runnable by pegasus-mpi-cluster.',
  'fix': 'Write pegasus.code.generator = PMC (plus sharedfs, transfer.links=true) into the properties file passed '
         'via --conf.'},
 {'id': 'pmc_rebuilt_with_mpicxx',
  'kind': 'require_if',
  'pattern': 'make\\s+[^\\n]*CXX=[^\\n]*mpicxx',
  'when': 'pegasus-mpi-cluster',
  'why': 'The prebuilt PMC is MPICH ABI v10 (libmpichcxx.so.10 not found against vendor MPI).',
  'fix': 'Rebuild: make CXX=$(which mpicxx) prefix=<pegasus> in packages/pegasus-mpi-cluster and overwrite '
         'bin/pegasus-mpi-cluster.'},
 {'id': 'pmc_rank_count',
  'kind': 'forbid',
  'pattern': '(flux\\s+run|srun|mpirun)\\b[^\\n]*\\s-n\\s*\\d{3,}[^\\n]*pegasus-mpi-cluster',
  'why': "Hundreds of ranks for a DAG with a few concurrent tasks hangs PMC's MPI_Init/worker registration.",
  'fix': 'Use -n about 2-4x the widest concurrent stage plus 1 master (e.g. -N4 -n32).'},
 {'id': 'no_dag_maxjobs_strip',
  'kind': 'forbid',
  'pattern': '(sed|grep\\s+-v)[^\\n]*(MAXJOBS|\\^JOB)[^\\n]*\\.dag',
  'why': 'Stripping MAXJOBS/JOB lines treats the symptom of a DAGMan DAG produced by a missing --conf.',
  'fix': 'Re-plan with --conf <pegasus.properties> and verify the DAG has only TASK/EDGE lines.'},
 {'id': 'no_sudo',
  'kind': 'forbid',
  'pattern': '^\\s*sudo\\b',
  'why': 'The whole stack installs in userspace under the session workspace.',
  'fix': 'Install Condor/Pegasus/PMC under the workspace without sudo.'}]
