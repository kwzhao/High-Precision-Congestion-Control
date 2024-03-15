use rayon::prelude::*;
use std::process::Command;

struct Parameters {
    shard: Vec<u32>,
    n_flows: Vec<u32>,
    n_hosts: Vec<u32>,
    dctcp_k: Vec<u32>,
    cc: Vec<String>,
}

fn main() -> anyhow::Result<()> {
    let base_rtt = 14400;
    let window = 18000;

    // use your own paths
    let python_path = format!("/data1/lichenni/software/anaconda3/envs/py27/bin/python");
    let root_path = format!("..");
    let output_dir = "/data2/lichenni/path_tc_empirical";
    let log_dir = format!("./logs");

    let file_traffic = format!("{}/traffic_gen/traffic_gen_by_n_empirical_tc.py", root_path);
    let file_reference = format!("{}/analysis/main_flowsim_mmf.py", root_path);
    let type_topo = "topo-pl";

    let params = Parameters {
        // shard: vec![0],
        shard: (0..50).collect(),
        n_flows: vec![20000],
        n_hosts: vec![3],
        dctcp_k: vec![30],
        cc: vec!["dctcp".to_string()],
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
