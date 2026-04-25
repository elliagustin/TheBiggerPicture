from datetime import datetime, UTC
import socket
import traceback
import json
from sqlalchemy import text
from helpers.mssql import get_engine


def execute_with_audit(
    process_name,
    func,
    batch_id,
    log_environment=None,
    subprocess_name=None,    
    *args,
    **kwargs
):
    engine = get_engine(database='tbpStaging')

    start_time = datetime.now(UTC)
    host_name = socket.gethostname()
    function_name = func.__name__

    parameters_payload = {
        "args": args,
        "kwargs": kwargs
    }

    insert_sql = text("""
        INSERT INTO tbpStaging.audit.ProcessExecutionLog
        (
            ProcessName,
            FunctionName,
            BatchID,
            LogEnvironment,
            SubProcessName,
            StartTimeUTC,
            Status,
            HostName,
            ProcessParameters
        )
        OUTPUT INSERTED.ProcessExecutionID
        VALUES
        (
            :ProcessName,
            :FunctionName,
            :BatchID,
            :LogEnvironment,
            :SubProcessName,
            :StartTimeUTC,
            :Status,
            :HostName,
            :ProcessParameters
        )
    """)

    with engine.begin() as conn:
        execution_id = conn.execute(
            insert_sql,
            {
                "ProcessName": process_name,
                "FunctionName": function_name,
                "BatchID":batch_id,
                "LogEnvironment": log_environment,
                "SubProcessName": subprocess_name,
                "StartTimeUTC": start_time,
                "Status": "RUNNING",
                "HostName": host_name,
                "ProcessParameters": json.dumps(parameters_payload, default=str)
            }
        ).scalar()

    try:
        result = func(*args, **kwargs)

        end_time = datetime.now(UTC)
        duration = (end_time - start_time).total_seconds()

        update_sql = text("""
            UPDATE tbpStaging.audit.ProcessExecutionLog
            SET EndTimeUTC = :EndTimeUTC,
                DurationSeconds = :DurationSeconds,
                Status = :Status
            WHERE ProcessExecutionID = :ExecutionID
        """)

        with engine.begin() as conn:
            conn.execute(update_sql, {
                "EndTimeUTC": end_time,
                "DurationSeconds": duration,
                "Status": "SUCCESS",
                "ExecutionID": execution_id
            })

        return result

    except Exception:
        end_time = datetime.now(UTC)
        duration = (end_time - start_time).total_seconds()
        error_message = traceback.format_exc()

        update_sql = text("""
            UPDATE tbpStaging.audit.ProcessExecutionLog
            SET EndTimeUTC = :EndTimeUTC,
                DurationSeconds = :DurationSeconds,
                Status = :Status,
                ErrorMessage = :ErrorMessage
            WHERE ProcessExecutionID = :ExecutionID
        """)

        with engine.begin() as conn:
            conn.execute(update_sql, {
                "EndTimeUTC": end_time,
                "DurationSeconds": duration,
                "Status": "FAILED",
                "ErrorMessage": error_message,
                "ExecutionID": execution_id
            })

        raise