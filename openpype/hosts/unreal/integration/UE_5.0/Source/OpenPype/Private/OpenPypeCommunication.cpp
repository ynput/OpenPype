#include "OpenPypeCommunication.h"
#include "OpenPype.h"
#include "GenericPlatform/GenericPlatformMisc.h"
#include "WebSocketsModule.h"
#include "JsonObjectConverter.h"


// Initialize static attributes
TSharedPtr<IWebSocket> FOpenPypeCommunication::Socket = nullptr;
TArray<FRpcResponse> FOpenPypeCommunication::RpcResponses = TArray<FRpcResponse>();
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

	FRpcResponse RpcResponse;

	if(!FJsonObjectConverter::JsonObjectStringToUStruct(Message, &RpcResponse, 0, 0)) {
		UE_LOG(LogTemp, Error, TEXT("Error during parsing message"));
		return;
	}

	RpcResponses.Add(RpcResponse);

	if (RpcResponse.error.code != 0)
	{
		UE_LOG(LogTemp, Error, TEXT("Error during calling method \"%s\""), *RpcResponse.error.message);
	}
	else
	{
		UE_LOG(LogTemp, Display, TEXT("Message parsed: %s"), *RpcResponse.result);
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
