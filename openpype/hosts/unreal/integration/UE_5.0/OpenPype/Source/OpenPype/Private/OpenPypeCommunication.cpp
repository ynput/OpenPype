#include "OpenPypeCommunication.h"
#include "OpenPype.h"
#include "GenericPlatform/GenericPlatformMisc.h"
#include "WebSocketsModule.h"
#include "Json.h"
#include "JsonObjectConverter.h"
#include "IPythonScriptPlugin.h"
#include "PythonScriptTypes.h"

#include <regex>


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
	UE_LOG(LogTemp, Warning, TEXT("Calling a function: %s"), *Method);

	TSharedPtr<FJsonObject> ParamsObject = Root->GetObjectField("params");

	TArray< TSharedPtr<FJsonValue> > FieldNames;
	ParamsObject->Values.GenerateValueArray(FieldNames);

	FString ParamStrings;

	// Checks if there are parameters in the params field.
	if (FieldNames.Num() > 0)
	{
		// If there are parameters, we serialize the params field to a string.
		TSharedRef< TJsonWriter<> > Writer = TJsonWriterFactory<>::Create(&ParamStrings);
		FJsonSerializer::Serialize(ParamsObject.ToSharedRef(), Writer);

		UE_LOG(LogTemp, Warning, TEXT("Parameters: %s"), *ParamStrings);

		// We need to escape the parameters string, because it will be used in a python command.
		// We use the std::regex library to do this.
		std::string ParamsStr(TCHAR_TO_UTF8(*ParamStrings));

		std::regex re;
		std::string str;

		re = std::regex("\\\\");
		str = std::regex_replace(ParamsStr, re, "/");

		re = std::regex("'");
		str = std::regex_replace(str, re, "\\'");

		re = std::regex("\"");
		str = std::regex_replace(str, re, "\\\"");

		// Fix true and false for python
		std::regex true_regex("\\btrue\\b");
		std::regex false_regex("\\bfalse\\b");
		str = std::regex_replace(str, true_regex, "True");
		str = std::regex_replace(str, false_regex, "False");

		// Fix null for python
		std::regex null_regex("\\bnull\\b");
		str = std::regex_replace(str, null_regex, "None");

		// We also need to remove the new line characters from the string, because
		// they will cause an error in the python command.
		std::string FormattedParamsStr;
		std::remove_copy(str.begin(), str.end(), std::back_inserter(FormattedParamsStr), '\n');

		ParamStrings = FString(UTF8_TO_TCHAR(FormattedParamsStr.c_str()));

		UE_LOG(LogTemp, Warning, TEXT("Formatted Parameters: %s"), *ParamStrings);

		ParamStrings = "\"\"\"" + ParamStrings + "\"\"\"";
	}

	// To execute the method from python, we need to construct the command
	// as a string. We use the FPythonCommandEx struct to do this. We set
	// the ExecutionMode to EvaluateStatement, so that the command is
	// executed as a statement.
	FPythonCommandEx Command;
	Command.ExecutionMode = EPythonCommandExecutionMode::EvaluateStatement;
	// Get the command from the params field, that is a python dict.
	Command.Command = Method + "(" + ParamStrings + ")";

	UE_LOG(LogTemp, Warning, TEXT("Full command: %s"), *Command.Command);

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

// void HandleJsonRpcRequest(const FString& JsonRpcRequest)
// {
//     TSharedPtr<FJsonObject> JsonObject;
//     TSharedRef<TJsonReader<>> JsonReader = TJsonReaderFactory<>::Create(JsonRpcRequest);

//     if (FJsonSerializer::Deserialize(JsonReader, JsonObject))
//     {
//         FString MethodName;
//         if (JsonObject->TryGetStringField("method", MethodName))
//         {
//             if (MethodName == "subtract")
//             {
//                 TSharedPtr<FJsonObject> ParamsObject = JsonObject->GetObjectField("params");
//                 int32 Minuend = ParamsObject->GetIntegerField("minuend");
//                 int32 Subtrahend = ParamsObject->GetIntegerField("subtrahend");

//                 int32 Difference = Minuend - Subtrahend;

//                 TSharedPtr<FJsonObject> ResponseObject = MakeShareable(new FJsonObject);
//                 ResponseObject->SetStringField("jsonrpc", "2.0");
//                 ResponseObject->SetObjectField("result", MakeShareable(new FJsonValueNumber(Difference)));
//                 ResponseObject->SetNumberField("id", JsonObject->GetNumberField("id"));

//                 FString JsonRpcResponse;
//                 TSharedRef<TJsonWriter<>> JsonWriter = TJsonWriterFactory<>::Create(&JsonRpcResponse);
//                 FJsonSerializer::Serialize(ResponseObject.ToSharedRef(), JsonWriter);

//                 // Send the JSON-RPC 2.0 response back to the client
//             }
//         }
//     }
// }
