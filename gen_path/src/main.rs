use rayon::prelude::*;
use std::process::Command;

struct Parameters {
    shard: Vec<u32>,
    n_flows: Vec<u32>,
    n_hosts: Vec<u32>,
    window: Vec<u32>,
    cc: Vec<String>,
    cc_param: Vec<u32>,
    bfsz_factor: Vec<String>,
}

fn main() -> anyhow::Result<()> {
    cc_param_map= {
        // dctcp_k
        "dctcp": vec![5, 30, 72],
        // timely
        "timely_vwin": vec![5, 30, 72],
        // dcqcn
        "dcqcn_paper_vwin": vec![5, 30, 72],
        // hp
        "hp": vec![5, 30, 72],
        // hpccPint
        "hpccPint": vec![5, 30, 72],
    };
    let base_rtt = 14400;
    // let window = 18000;
    let keynote = "_path_tc";
    let python_path = format!("/data1/lichenni/software/anaconda3/envs/py27/bin/python");
    let root_path = format!(
        "/data1/lichenni/projects/flow_simulation/parsimon/backends/High-Precision-Congestion-Control",
    );
    let output_dir = "/data2/lichenni/path_tc";
    let log_dir = format!("./log{}", keynote);

    // let file_traffic = format!("{}/traffic_gen/traffic_gen_by_n_synthetic.py", root_path);
    let file_traffic = format!("{}/traffic_gen/traffic_gen_by_n_synthetic_tc.py", root_path);
    let file_sim = format!("{}/simulation/run_by_n.py", root_path);
    let file_ns3 = format!("{}/analysis/fct_to_file.py", root_path);
    let file_reference = format!("{}/analysis/main_flowsim_mmf.py", root_path);
    // let file_reference_link = format!("{}/analysis/main_flowsim_mmf_link.py", root_path);
    let type_topo = "topo-pl";

    let params = Parameters {
        // shard: vec![0],
        shard: (0..2000).collect(),
        // n_flows: vec![20],
        n_flows: vec![20000],
        // n_hosts: vec![3,7],
        n_hosts: vec![3, 5, 7],
        // dctcp_k: vec![5, 12, 15, 19, 22, 27, 30, 36, 43, 46, 52, 57, 62, 68, 72],
        // dctcp_k: vec![5, 30, 72],
        // window: vec![5, 9, 15, 18, 22, 27, 30, 36, 45, 50].iter().map(|x| x * 1000).collect(),
        window: vec![18].iter().map(|x| x * 1000).collect(),
        // cc: vec!["dctcp".to_string()],
        cc: vec!["dctcp".to_string(),"timely_vwin".to_string(),"dcqcn_paper_vwin".to_string(), "hp".to_string(), "hpccPint".to_string()],
        bfsz_factor: vec![1.0],
    };
    // println!("{:?}", Parameters::field_names());
    itertools::iproduct!(&params.shard, &params.n_flows, &params.n_hosts)
        .par_bridge()
        .for_each(|combination| {
            let shard = combination.0;
            let n_flows = combination.1;
            let n_hosts = combination.2;

            // println!("{:?}", combination);
            let scenario_dir = format!(
                "shard{}_nflows{}_nhosts{}_lr10Gbps",
                shard, n_flows, n_hosts,
            );
            let output_path = format!("{}/{}", output_dir, scenario_dir);

            // gen traffic
            let command_args = format!(
                "--shard {} -f {} -n {} -b 10G -o {} --switchtohost 4",
                shard, n_flows, n_hosts, output_path,
            );
            let log_path = format!("{}/nhosts{}_traffic.log", log_dir, n_hosts);
            let py_command = format!("{} {} {}", python_path, file_traffic, command_args);
            let cmd = format!(
                "echo {} >> {}; {} >> {}; echo \"\">>{}",
                py_command, log_path, py_command, log_path, log_path
            );
            // println!("{}", cmd);
            let mut child = Command::new("sh").arg("-c").arg(cmd).spawn().unwrap();
            let mut _result = child.wait().unwrap();
        });

    // println!("{:?}", Parameters::field_names());
    itertools::iproduct!(
        &params.window,
        &params.shard,
        &params.n_flows,
        &params.n_hosts,
        &params.cc,
        &params.bfsz_factor
    )
    .par_bridge()
    .for_each(|combination| {
        let window = combination.0;
        let shard = combination.1;
        let n_flows = combination.2;
        let n_hosts = combination.3;
        let cc= combination.4;
        let bfsz_factor = combination.5;

        println!("{:?}", combination);
        let scenario_dir = format!(
            "shard{}_nflows{}_nhosts{}_lr10Gbps",
            shard, n_flows, n_hosts,
        );

        // ns3 sim
        let mut command_args = format!(
            "--cc {} --trace flows --bw 10 --fwin {} --base_rtt {} \
            --topo {}-{}  --root {}/{} --bfsz_factor {}",cc,
            window, base_rtt, type_topo, n_hosts, output_dir, scenario_dir, bfsz_factor
        );
        let mut log_path = format!("{}/nhosts{}_sim.log", log_dir, n_hosts,);
        let mut py_command = format!("{} {} {}", python_path, file_sim, command_args,);
        let mut cmd = format!(
            "echo {} >> {}; {} >> {}; echo \"\">>{}",
            py_command, log_path, py_command, log_path, log_path
        );
        // println!("{}", cmd);
        let mut child = Command::new("sh").arg("-c").arg(cmd).spawn().unwrap();
        let mut _result = child.wait().unwrap();

        // parse ground-truth
        command_args = format!(
            "--shard {} --cc {} -b 10 -p {}-{} --output_dir {} --scenario_dir {} --fwin {} --bfsz_factor {}",
            shard, cc, type_topo, n_hosts, output_dir, scenario_dir, window, bfsz_factor
        );
        log_path = format!("{}/nhosts{}_ns3.log", log_dir, n_hosts,);
        py_command = format!("{} {} {}", python_path, file_ns3, command_args,);
        cmd = format!(
            "echo {} >> {}; {} >> {}; echo \"\">>{}",
            py_command, log_path, py_command, log_path, log_path
        );
        // println!("{}", cmd);
        child = Command::new("sh").arg("-c").arg(cmd).spawn().unwrap();
        _result = child.wait().unwrap();
    });

    // println!("{:?}", Parameters::field_names());
    itertools::iproduct!(&params.shard, &params.n_flows, &params.n_hosts)
        .par_bridge()
        .for_each(|combination| {
            let shard = combination.0;
            let n_flows = combination.1;
            let n_hosts = combination.2;

            // println!("{:?}", combination);
            let scenario_dir = format!(
                "shard{}_nflows{}_nhosts{}_lr10Gbps",
                shard, n_flows, n_hosts,
            );

            // run reference sys (e.g., max-min fair sharing)
            let command_args = format!(
                "--shard {} -b 10 -p {}-{} --output_dir {} --scenario_dir {} --nhost {}",
                shard, type_topo, n_hosts, output_dir, scenario_dir, n_hosts,
            );
            let log_path = format!("{}/nhosts{}_reference.log", log_dir, n_hosts,);
            let py_command = format!("{} {} {}", python_path, file_reference, command_args,);
            let cmd = format!(
                "echo {} >> {}; {} >> {}; echo \"\">>{}",
                py_command, log_path, py_command, log_path, log_path
            );
            // println!("{}", cmd);
            let mut child = Command::new("sh").arg("-c").arg(cmd).spawn().unwrap();
            let mut _result = child.wait().unwrap();
        });

    Ok(())
}
