use rayon::prelude::*;
use std::process::Command;

struct Parameters {
    shard: Vec<u32>,
    n_flows: Vec<u32>,
    n_hosts: Vec<u32>,
    shard_cc: Vec<u32>
}

fn main() -> anyhow::Result<()> {
    let base_rtt = 14400;
    let enable_tr = 0;
    let enable_debug = 0;
    
    // use your own paths
    let python_path = format!("/data1/lichenni/software/anaconda3/envs/py27/bin/python");
    let output_dir = format!("/data2/lichenni/path_tc");
    
    let root_path = format!("..");
    let log_dir = format!("./logs");
    let file_traffic = format!("{}/traffic_gen/traffic_gen_synthetic.py", root_path);
    let file_sim = format!("{}/simulation/run_by_n.py", root_path);
    let file_ns3 = format!("{}/analysis/fct_to_file.py", root_path);
    let file_reference = format!("{}/analysis/main_flowsim_mmf.py", root_path);
    let type_topo = "topo-pl";

    let params = Parameters {
        // shard: vec![0],
        shard: (0..2000).collect(),
        n_flows: vec![20000],
        // n_flows: vec![1000],
        // n_hosts: vec![3],
        n_hosts: vec![3, 5, 7],
        // shard_cc: vec![0],
        shard_cc: (0..20).collect(),
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
        &params.shard,
        &params.n_flows,
        &params.n_hosts,
        &params.shard_cc
    )
    .par_bridge()
    .for_each(|combination| {
        let shard = combination.0;
        let n_flows = combination.1;
        let n_hosts = combination.2;
        let shard_cc = combination.3;

        println!("{:?}", combination);
        let scenario_dir = format!(
            "shard{}_nflows{}_nhosts{}_lr10Gbps",
            shard, n_flows, n_hosts,
        );

        // ns3 sim
        let mut command_args = format!(
            "--trace flows --bw 10 --base_rtt {} \
            --topo {}-{}  --root {}/{} --shard_cc {} --enable_tr {} --enable_debug {}",base_rtt, type_topo, n_hosts, output_dir, scenario_dir, shard_cc, enable_tr, enable_debug,
        );
        let mut log_path = format!("{}/nhosts{}_sim.log", log_dir, n_hosts,);
        let mut py_command = format!("{} {} {}", python_path, file_sim, command_args,);
        let mut cmd = format!(
            "echo {} >> {}; {} >> {}/{}/pdrop_{}-{}_s{}.txt",
            py_command, log_path, py_command, output_dir, scenario_dir,type_topo, n_hosts, shard_cc
        );
        // let mut cmd = format!(
        //     "echo {} >> {}; {} >> {}; echo \"\">>{}",
        //     py_command, log_path, py_command, log_path, log_path
        // );
        // println!("{}", cmd);
        let mut child = Command::new("sh").arg("-c").arg(cmd).spawn().unwrap();
        let mut _result = child.wait().unwrap();

        // parse ground-truth
        command_args = format!(
            "--shard {} -b 10 -p {}-{} --output_dir {} --scenario_dir {} --shard_cc {} --enable_debug {}",
            shard, type_topo, n_hosts, output_dir, scenario_dir, shard_cc,enable_debug
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
