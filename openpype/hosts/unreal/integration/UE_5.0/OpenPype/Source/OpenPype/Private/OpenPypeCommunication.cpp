#include "OpenPypeCommunication.h"
#include "OpenPype.h"
#include "GenericPlatform/GenericPlatformMisc.h"
#include "WebSocketsModule.h"
#include "Json.h"
#include "JsonObjectConverter.h"
#include "IPythonScriptPlugin.h"
#include "PythonScriptTypes.h"


// Initialize static attributes
TSharedPtr<IWebSocket> FOpenPypeCommunication::Socket = nullptr;
int32 FOpenPypeCommunication::Id = 0;

void FOpenPypeCommunication::CreateSocket()
{
	UE_LOG(LogTemp, Display, TEXT("Creating web socket..."));

	FString url = FWindowsPlatformMisc::GetEnvironmentVariable(*FString("WEBSOCKET_URL"));

	UE_LOG(LogTemp, Display, TEXT("Websocket URL: %s"), *url);

	const FString ServerURL = url;
	const FString ServerProtocol = TEXT("ws");

	// We initialize the Id to 0. This is used during the communication to
	// identify the message and the responses.
	Id = 0;
	Socket = FWebSocketsModule::Get().CreateWebSocket(ServerURL, ServerProtocol);
}

void FOpenPypeCommunication::ConnectToSocket()
{
	// Handle delegates for the socket.
	Socket->OnConnected().AddStatic(&FOpenPypeCommunication::OnConnected);
	Socket->OnConnectionError().AddStatic(&FOpenPypeCommunication::OnConnectionError);
	Socket->OnClosed().AddStatic(&FOpenPypeCommunication::OnClosed);
	Socket->OnMessage().AddStatic(&FOpenPypeCommunication::OnMessage);
	Socket->OnMessageSent().AddStatic(&FOpenPypeCommunication::OnMessageSent);

	UE_LOG(LogTemp, Display, TEXT("Attempting to connect to web socket server..."));

	Socket->Connect();
}

void FOpenPypeCommunication::CloseConnection()
{
	Socket->Close();
}

bool FOpenPypeCommunication::IsConnected()
{
	return Socket->IsConnected();
}

void FOpenPypeCommunication::CallMethod(const FString Method, const TArray<FString> Args)
{
	if (Socket->IsConnected())
	{
		UE_LOG(LogTemp, Verbose, TEXT("Calling method \"%s\"..."), *Method);

		int32 newId = Id++;

		FString Message;
		FRpcCall RpcCall = { "2.0", *Method, Args, newId };
		FJsonObjectConverter::UStructToJsonObjectString(RpcCall, Message);

		Socket->Send(Message);
	}
	else
	{
		UE_LOG(LogTemp, Error, TEXT("Error calling method \"%s\"..."), *Method);
	}
}

void FOpenPypeCommunication::OnConnected()
{
	// This code will run once connected.
	UE_LOG(LogTemp, Warning, TEXT("Connected to web socket server."));
}

void FOpenPypeCommunication::OnConnectionError(const FString & Error)
{
	// This code will run if the connection failed. Check Error to see what happened.
	UE_LOG(LogTemp, Error, TEXT("Error during connection."));
	UE_LOG(LogTemp, Error, TEXT("%s"), *Error);
}

void FOpenPypeCommunication::OnClosed(int32 StatusCode, const FString& Reason, bool bWasClean)
{
	// This code will run when the connection to the server has been terminated.
	// Because of an error or a call to Socket->Close().
	UE_LOG(LogTemp, Warning, TEXT("Closed connection to web socket server."));
}

void FOpenPypeCommunication::OnMessage(const FString & Message)
{
	// This code will run when we receive a string message from the server.
	UE_LOG(LogTemp, Verbose, TEXT("Message received: \"%s\"."), *Message);

	TSharedRef< TJsonReader<> > Reader = TJsonReaderFactory<>::Create(Message);
	TSharedPtr<FJsonObject> Root;

	if (FJsonSerializer::Deserialize(Reader, Root))
	{
		// Depending on the fields of the received message, we handle the
		// message differently.
		if (Root->HasField(TEXT("method")))
		{
			RunMethod(Root);
		}
		else if (Root->HasField(TEXT("result")))
		{
			HandleResult(Root);
		}
		else if (Root->HasField(TEXT("error")))
		{
			HandleError(Root);
		}
		else
		{
			UE_LOG(LogTemp, Error, TEXT("Error during parsing message"));
		}
	}
	else
	{
		UE_LOG(LogTemp, Error, TEXT("Error during deserialization"));
	}
}

void FOpenPypeCommunication::OnMessageSent(const FString& MessageString)
{
	// This code is called after we sent a message to the server.
	UE_LOG(LogTemp, Verbose, TEXT("Message sent: %s"), *MessageString);
}

void FOpenPypeCommunication::HandleResult(TSharedPtr<FJsonObject> Root)
{
	// This code is called when we receive a result from the server.
	UE_LOG(LogTemp, Verbose, TEXT("Getting a result."));

	FString OutputMessage;
	if (Root->TryGetStringField(TEXT("result"), OutputMessage))
	{
		UE_LOG(LogTemp, Verbose, TEXT("Result: %s"), *OutputMessage);
	}
	else
	{
		UE_LOG(LogTemp, Verbose, TEXT("Function call successful without return value"));
	}
}

void FOpenPypeCommunication::HandleError(TSharedPtr<FJsonObject> Root)
{
	// This code is called when we receive an error from the server.
	UE_LOG(LogTemp, Verbose, TEXT("Getting an error."));

	auto Error = Root->GetObjectField(TEXT("error"));

	if (Error->HasField(TEXT("message")))
	{
		FString ErrorMessage;
		Error->TryGetStringField(TEXT("message"), ErrorMessage);
		UE_LOG(LogTemp, Error, TEXT("Error: %s"), *ErrorMessage);
	}
	else
	{
		UE_LOG(LogTemp, Error, TEXT("Error during parsing error"));
	}
}

void FOpenPypeCommunication::RunMethod(TSharedPtr<FJsonObject> Root)
{
	// This code is called when we receive the request to run a method from the server.
	IPythonScriptPlugin* PythonPlugin = IPythonScriptPlugin::Get();

	if ( !PythonPlugin || !PythonPlugin->IsPythonAvailable() )
	{
        UE_LOG(LogTemp, Error, TEXT("Python Plugin not loaded!"));
		return;
	}

	FString Method = Root->GetStringField(TEXT("method"));
	UE_LOG(LogTemp, Verbose, TEXT("Calling a function: %s"), *Method);

	FPythonCommandEx Command;
	Command.ExecutionMode = EPythonCommandExecutionMode::EvaluateStatement;
	Command.Command = Method + "(";
	auto params = Root->GetArrayField(TEXT("params"));
	for (auto param : params)
	{
		Command.Command += " " + param->AsString() + ",";
	}
	Command.Command += ")";

	UE_LOG(LogTemp, Verbose, TEXT("Full command: %s"), *Command.Command);

	FString StringResponse;

	if ( !PythonPlugin->ExecPythonCommandEx(Command) )
	{
		UE_LOG(LogTemp, Error, TEXT("Python Execution Failed!"));
		for ( FPythonLogOutputEntry& LogEntry : Command.LogOutput )
		{
			UE_LOG(LogTemp, Error, TEXT("%s"), *LogEntry.Output);
		}

		FRpcError RpcError = { -32000, "Python Execution in Unreal Failed!", "" };
		FRpcResponseError RpcResponse = { "2.0", RpcError, Root->GetIntegerField(TEXT("id")) };
		FJsonObjectConverter::UStructToJsonObjectString(RpcResponse, StringResponse);
	}
	else
	{
		UE_LOG(LogTemp, Verbose, TEXT("Python Execution Success!"));
		UE_LOG(LogTemp, Verbose, TEXT("Result: %s"), *Command.CommandResult);

		FRpcResponseResult RpcResponse = { "2.0", Command.CommandResult, Root->GetIntegerField(TEXT("id")) };
		FJsonObjectConverter::UStructToJsonObjectString(RpcResponse, StringResponse);
	}

	Socket->Send(StringResponse);
}
