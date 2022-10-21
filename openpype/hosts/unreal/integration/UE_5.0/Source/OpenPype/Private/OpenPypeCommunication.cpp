#include "OpenPypeCommunication.h"
#include "OpenPype.h"
#include "GenericPlatform/GenericPlatformMisc.h"
#include "WebSocketsModule.h"
#include "Json.h"
#include "JsonObjectConverter.h"


// Initialize static attributes
TSharedPtr<IWebSocket> FOpenPypeCommunication::Socket = nullptr;
int32 FOpenPypeCommunication::Id = 0;

void FOpenPypeCommunication::CreateSocket()
{
	UE_LOG(LogTemp, Display, TEXT("Starting web socket..."));

	FString url = FWindowsPlatformMisc::GetEnvironmentVariable(*FString("WEBSOCKET_URL"));

	UE_LOG(LogTemp, Display, TEXT("Websocket URL: %s"), *url);

	const FString ServerURL = url;
	const FString ServerProtocol = TEXT("ws");

	TMap<FString, FString> UpgradeHeaders;
	UpgradeHeaders.Add(TEXT("upgrade"), TEXT("websocket"));

	Id = 0;
	Socket = FWebSocketsModule::Get().CreateWebSocket(ServerURL, ServerProtocol, UpgradeHeaders);
}

void FOpenPypeCommunication::ConnectToSocket()
{
	Socket->OnConnected().AddStatic(&FOpenPypeCommunication::OnConnected);
	Socket->OnConnectionError().AddStatic(&FOpenPypeCommunication::OnConnectionError);
	Socket->OnClosed().AddStatic(&FOpenPypeCommunication::OnClosed);
	Socket->OnMessage().AddStatic(&FOpenPypeCommunication::OnMessage);
	Socket->OnRawMessage().AddStatic(&FOpenPypeCommunication::OnRawMessage);
	Socket->OnMessageSent().AddStatic(&FOpenPypeCommunication::OnMessageSent);

	UE_LOG(LogTemp, Display, TEXT("Connecting web socket to server..."));

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
		UE_LOG(LogTemp, Display, TEXT("Calling method \"%s\"..."), *Method);

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
	UE_LOG(LogTemp, Warning, TEXT("Connected"));
}

void FOpenPypeCommunication::OnConnectionError(const FString & Error)
{
	// This code will run if the connection failed. Check Error to see what happened.
	UE_LOG(LogTemp, Error, TEXT("Error during connection"));
	UE_LOG(LogTemp, Error, TEXT("%s"), *Error);
}

void FOpenPypeCommunication::OnClosed(int32 StatusCode, const FString& Reason, bool bWasClean)
{
	// This code will run when the connection to the server has been terminated.
	// Because of an error or a call to Socket->Close().
	UE_LOG(LogTemp, Warning, TEXT("Closed"));
}

void FOpenPypeCommunication::OnMessage(const FString & Message)
{
	// This code will run when we receive a string message from the server.
	UE_LOG(LogTemp, Display, TEXT("Message received: %s"), *Message);

	TSharedRef< TJsonReader<> > Reader = TJsonReaderFactory<>::Create(Message);
	TSharedPtr<FJsonObject> Root;

	if (FJsonSerializer::Deserialize(Reader, Root))
	{
		if (Root->HasField(TEXT("method")))
		{
			FString Method = Root->GetStringField(TEXT("method"));
			UE_LOG(LogTemp, Display, TEXT("Method: %s"), *Method);

			if (Method == "ls")
			{
				FString Result = UOpenPypePythonBridge::Get()->ls();

				UE_LOG(LogTemp, Display, TEXT("Result: %s"), *Result);

				FString StringResponse;
				FRpcResponseResult RpcResponse = { "2.0", Result, Root->GetIntegerField(TEXT("id")) };
				FJsonObjectConverter::UStructToJsonObjectString(RpcResponse, StringResponse);

				Socket->Send(StringResponse);
			}
			else if (Method == "containerise")
			{
				auto params = Root->GetArrayField(TEXT("params"));

				FString Name = params[0]->AsString();
				FString Namespace = params[1]->AsString();
				FString Nodes = params[2]->AsString();
				FString Context = params[3]->AsString();
				FString Loader = params.Num() >= 5 ? params[4]->AsString() : TEXT("");
				FString Suffix = params.Num() == 6 ? params[5]->AsString() : TEXT("_CON");

				UE_LOG(LogTemp, Display, TEXT("Name: %s"), *Name);
				UE_LOG(LogTemp, Display, TEXT("Namespace: %s"), *Namespace);
				UE_LOG(LogTemp, Display, TEXT("Nodes: %s"), *Nodes);
				UE_LOG(LogTemp, Display, TEXT("Context: %s"), *Context);
				UE_LOG(LogTemp, Display, TEXT("Loader: %s"), *Loader);
				UE_LOG(LogTemp, Display, TEXT("Suffix: %s"), *Suffix);

				FString Result = UOpenPypePythonBridge::Get()->containerise(Name, Namespace, Nodes, Context, Loader, Suffix);

				UE_LOG(LogTemp, Display, TEXT("Result: %s"), *Result);

				FString StringResponse;
				FRpcResponseResult RpcResponse = { "2.0", Result, Root->GetIntegerField(TEXT("id")) };
				FJsonObjectConverter::UStructToJsonObjectString(RpcResponse, StringResponse);

				Socket->Send(StringResponse);
			}
			else if (Method == "instantiate")
			{
				auto params = Root->GetArrayField(TEXT("params"));

				FString RootParam = params[0]->AsString();
				FString Name = params[1]->AsString();
				FString Data = params[2]->AsString();
				FString Assets = params.Num() >= 4 ? params[3]->AsString() : TEXT("");
				FString Suffix = params.Num() == 5 ? params[4]->AsString() : TEXT("_INS");

				UE_LOG(LogTemp, Display, TEXT("Root: %s"), *RootParam);
				UE_LOG(LogTemp, Display, TEXT("Name: %s"), *Name);
				UE_LOG(LogTemp, Display, TEXT("Data: %s"), *Data);
				UE_LOG(LogTemp, Display, TEXT("Assets: %s"), *Assets);
				UE_LOG(LogTemp, Display, TEXT("Suffix: %s"), *Suffix);

				UOpenPypePythonBridge::Get()->instantiate(RootParam, Name, Data, Assets, Suffix);

				FString StringResponse;
				FRpcResponseResult RpcResponse = { "2.0", "", Root->GetIntegerField(TEXT("id")) };
				FJsonObjectConverter::UStructToJsonObjectString(RpcResponse, StringResponse);

				Socket->Send(StringResponse);
			}
		}
		else if (Root->HasField(TEXT("result")))
		{
			FString OutputMessage;
			if (Root->TryGetStringField(TEXT("result"), OutputMessage))
			{
				UE_LOG(LogTemp, Display, TEXT("Result: %s"), *OutputMessage);
			}
			else
			{
				UE_LOG(LogTemp, Display, TEXT("Function call successful without return value"));
			}
		}
		else if (Root->HasField(TEXT("error")))
		{
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

void FOpenPypeCommunication::OnRawMessage(const void* Data, SIZE_T Size, SIZE_T BytesRemaining)
{
	// This code will run when we receive a raw (binary) message from the server.
	UE_LOG(LogTemp, Display, TEXT("Raw message received"));
}

void FOpenPypeCommunication::OnMessageSent(const FString& MessageString)
{
	// This code is called after we sent a message to the server.
	UE_LOG(LogTemp, Display, TEXT("Message sent: %s"), *MessageString);
}
