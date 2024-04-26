use rayon::prelude::*;
use std::process::Command;
use clap::Parser;
use std::path::PathBuf;
use std::fs;
struct Parameters {
    shard: Vec<u32>,
    n_flows: Vec<u32>,
    n_hosts: Vec<u32>,
    shard_cc: Vec<u32>,
    bandwidth: Vec<u32>,
    prop_delay: Vec<u32>,
}

#[derive(Debug, Parser)]
pub struct Main {
    #[clap(long, default_value = "/data1/lichenni/software/anaconda3/envs/py39/bin/python")]
    python_path: PathBuf,
    #[clap(long, default_value = "/data2/lichenni/test")]
    output_dir: PathBuf,
}

fn main() -> anyhow::Result<()> {
    let args = Main::parse();
    let python_path = args.python_path.display().to_string();
    let output_dir = args.output_dir.display().to_string();

    println!("python_path: {:?}, output_dir: {:?}", python_path,output_dir);

    let base_rtt = 14400;
    let enable_tr = 1;
    let enable_debug = 0;
    let constfsize=1000000;
    // setup the configurations
    let params = Parameters {
        shard: (0..1).collect(),
        // n_flows: vec![20000],
        n_flows: (1..=9).step_by(2).collect(),
        // n_hosts: vec![3, 5, 7],
        n_hosts: vec![3],
        shard_cc: (0..12000).collect(),
        bandwidth: (1..=9).step_by(2).collect(),
        prop_delay: (1000..=9000).step_by(2000).collect(),
    };

    // config for debugging
    // let params = Parameters {
    //     shard: vec![0],
    //     n_flows: vec![1],
    //     // n_flows: (1..=9).step_by(2).collect(),
    //     n_hosts: vec![3],
    //     shard_cc: vec![0],
    //     bandwidth: vec![1],
    //     // bandwidth: (1..=9).step_by(2).collect(),
    //     prop_delay: vec![10000],
    //     // prop_delay: (1000..=9000).step_by(2000).collect(),
    // };

    // no need to change
    let root_path = format!("..");
    let log_dir = "./logs_cc";
    if let Err(err) = fs::create_dir_all(log_dir) {
        eprintln!("Error creating directory '{}': {}", log_dir, err);
    } else {
        println!("Directory '{}' created successfully.", log_dir);
    }

    let file_traffic = format!("{}/traffic_gen/traffic_gen_synthetic.py", root_path);
    let file_sim = format!("{}/simulation/run_cc.py", root_path);
    let file_ns3 = format!("{}/analysis/fct_to_file_cc.py", root_path);
    // let file_reference = format!("{}/analysis/main_flowsim_mmf.py", root_path);
    let type_topo = "topo-pl";

    // println!("{:?}", Parameters::field_names());
    itertools::iproduct!(&params.shard, &params.n_flows, &params.n_hosts)
        .par_bridge()
        .for_each(|combination| {
            let shard = combination.0;
            let n_flows = combination.1;
            let n_hosts = combination.2;

            // println!("{:?}", combination);
            let scenario_dir = format!(
                "shard{}_nflows{}_nhosts{}",
                shard, n_flows, n_hosts,
            );
            let output_path = format!("{}/{}", output_dir, scenario_dir);

            // gen traffic
            let command_args = format!(
                "--shard {} -f {} -n {} -b 10G -o {} --switchtohost 4 --constfsize {}",
                shard, n_flows, n_hosts, output_path,constfsize,
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
        &params.shard_cc,
        &params.bandwidth,
        &params.prop_delay
    )
    .par_bridge()
    .for_each(|combination| {
        let shard = combination.0;
        let n_hosts = combination.2;
        let shard_cc = combination.3;
        let shard_total = shard * params.shard_cc.len() as u32 + shard_cc;
        let n_flows = combination.1;
        let bandwidth = combination.4;
        let prop_delay = combination.5;

        println!("{:?}", combination);
        let scenario_dir = format!(
            "shard{}_nflows{}_nhosts{}",
            shard, n_flows, n_hosts,
        );

        // ns3 sim
        let mut command_args = format!(
            "--trace flows --base_rtt {} \
            --topo {}-{}  --root {}/{} --shard_cc {} --shard_total {} --enable_tr {} --enable_debug {} --bw {} --pd {} ", base_rtt, type_topo, n_hosts, output_dir, scenario_dir, shard_cc, shard_total, enable_tr, enable_debug,bandwidth,prop_delay
        );
        let mut log_path = format!("{}/nhosts{}_sim.log", log_dir, n_hosts,);
        let mut py_command = format!("{} {} {}", python_path, file_sim, command_args,);
        let mut cmd = format!(
            "echo {} >> {}; {} >> {}/{}/pdrop_{}-{}-{}-{}_s{}.txt",
            py_command, log_path, py_command, output_dir, scenario_dir,type_topo, n_hosts, bandwidth,prop_delay, shard_cc
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
            "--shard {} -p {}-{}-{}-{} --output_dir {} --scenario_dir {} --shard_cc {} --enable_debug {}",
            shard, type_topo, n_hosts, bandwidth,prop_delay, output_dir, scenario_dir, shard_cc,enable_debug
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
    // itertools::iproduct!(&params.shard, &params.n_flows, &params.n_hosts)
    //     .par_bridge()
    //     .for_each(|combination| {
    //         let shard = combination.0;
    //         let n_flows = combination.1;
    //         let n_hosts = combination.2;

    //         // println!("{:?}", combination);
    //         let scenario_dir = format!(
    //             "shard{}_nflows{}_nhosts{}",
    //             shard, n_flows, n_hosts,
    //         );

    //         // run reference sys (e.g., max-min fair sharing)
    //         let command_args = format!(
    //             "--shard {} -b {} -p {}-{} --output_dir {} --scenario_dir {} --nhost {}",
    //             shard, bandwidth, type_topo, n_hosts, output_dir, scenario_dir, n_hosts,
    //         );
    //         let log_path = format!("{}/nhosts{}_reference.log", log_dir, n_hosts,);
    //         let py_command = format!("{} {} {}", python_path, file_reference, command_args,);
    //         let cmd = format!(
    //             "echo {} >> {}; {} >> {}; echo \"\">>{}",
    //             py_command, log_path, py_command, log_path, log_path
    //         );
    //         // println!("{}", cmd);
    //         let mut child = Command::new("sh").arg("-c").arg(cmd).spawn().unwrap();
    //         let mut _result = child.wait().unwrap();
    //     });

    Ok(())
}
