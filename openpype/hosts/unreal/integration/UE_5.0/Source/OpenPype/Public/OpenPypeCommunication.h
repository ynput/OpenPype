// Copyright 1998-2019 Epic Games, Inc. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "IWebSocket.h"       // Socket definition

#include "OpenPypeCommunication.generated.h"


USTRUCT()
struct FRpcCall
{
    GENERATED_BODY()

public:
    UPROPERTY()
    FString jsonrpc;

    UPROPERTY()
    FString method;

	UPROPERTY()
	TArray<FString> params;

    UPROPERTY()
    int32 id;
};

USTRUCT()
struct FRpcError
{
    GENERATED_BODY()

public:
    UPROPERTY()
    int32 code;

    UPROPERTY()
    FString message;

	UPROPERTY()
	FString data;
};

USTRUCT()
struct FRpcResponse
{
    GENERATED_BODY()

public:
    UPROPERTY()
    FString jsonrpc;

    UPROPERTY()
    FString result;

	UPROPERTY()
	struct FRpcError error;

    UPROPERTY()
    int32 id;
};

class FOpenPypeCommunication
{
public:
	static void CreateSocket();
	static void ConnectToSocket();
    static void CloseConnection();

	static bool IsConnected();

    static void CallMethod(const FString Method, const TArray<FString> Args);

public:
    UFUNCTION()
    static void OnConnected();

    UFUNCTION()
    static void OnConnectionError(const FString & Error);

    UFUNCTION()
    static void OnClosed(int32 StatusCode, const FString& Reason, bool bWasClean);

    UFUNCTION()
    static void OnMessage(const FString & Message);

    UFUNCTION()
    static void OnRawMessage(const void* Data, SIZE_T Size, SIZE_T BytesRemaining);

    UFUNCTION()
    static void OnMessageSent(const FString& MessageString);

private:
	static TSharedPtr<IWebSocket> Socket;
    static TArray<FRpcResponse> RpcResponses;
    static int32 Id;
};
