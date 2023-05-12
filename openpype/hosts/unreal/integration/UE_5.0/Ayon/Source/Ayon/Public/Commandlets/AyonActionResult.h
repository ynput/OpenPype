// Copyright 2023, Ayon, All rights reserved.

#pragma once

#include "CoreMinimal.h"
#include "AyonActionResult.generated.h"

/**
 * @brief This macro returns error code when is problem or does nothing when there is no problem.
 * @param ActionResult FAyon_ActionResult structure
 */
#define EVALUATE_Ayon_ACTION_RESULT(ActionResult) \
	if(ActionResult.IsProblem()) \
		return ActionResult.GetStatus();

/**
* @brief This enum values are humanly readable mapping of error codes.
* Here should be all error codes to be possible find what went wrong.
* TODO: In the future should exists an web document where is mapped error code & what problem occured & how to repair it...
*/
UENUM()
namespace EAyon_ActionResult
{
	enum Type
	{
		Ok,
		ProjectNotCreated,
		ProjectNotLoaded,
		ProjectNotSaved,
		//....Here insert another values 

		//Do not remove!
		//Usable for looping through enum values
		__Last UMETA(Hidden) 
	};
}


/**
 * @brief This struct holds action result enum and optionally reason of fail
 */
USTRUCT()
struct FAyon_ActionResult
{
	GENERATED_BODY()

public:
	/**	 @brief Default constructor usable when there is no problem */
	FAyon_ActionResult();

	/**
	 * @brief This constructor initializes variables & attempts to log when is error
	 * @param InEnum Status
	 */
	FAyon_ActionResult(const EAyon_ActionResult::Type& InEnum);

	/**
	 * @brief This constructor initializes variables & attempts to log when is error
	 * @param InEnum Status
	 * @param InReason Reason of potential fail
	 */
	FAyon_ActionResult(const EAyon_ActionResult::Type& InEnum, const FText& InReason);

private:
	/** @brief Action status  */
	EAyon_ActionResult::Type Status;	

	/** @brief Optional reason of fail	 */
	FText Reason;	

public:
	/**
	 * @brief Checks if there is problematic state
	 * @return true when status is not equal to EAyon_ActionResult::Ok
	 */
	bool IsProblem() const;
	EAyon_ActionResult::Type& GetStatus();
	FText& GetReason();

private:	
	void TryLog() const;
};

